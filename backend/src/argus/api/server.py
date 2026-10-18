"""ARGUS PRISM: REST API Server bridging the Core Engine to Web & Next.js Frontends."""

import base64
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from argus.engine.academic_exporter import AcademicExporter
from argus.engine.audit_report import AuditReportGenerator
from argus.engine.auto_fixer import FactualAutoFixer
from argus.engine.badge_generator import BadgeGenerator
from argus.engine.evaluator import ResearchEvaluator
from argus.engine.url_crawler import WebpageAuditor
from argus.models.domain import ValidationVerdict
from argus.observability.sentry_tracer import SentryTracer
from argus.providers import get_provider
from argus.providers.cache import SerpApiCache

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="ARGUS PRISM API",
    description="Deterministic Evidence Intelligence REST API for Next.js & Web Studio",
    version="0.1.0",
)

# Enable CORS dynamically via environment variable
raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
if raw_origins.strip() == "*":
    ALLOWED_ORIGINS = ["*"]
elif raw_origins:
    ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.onrender\.com"),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------------------------

class ValidateRequest(BaseModel):
    text: Optional[str] = Field(None, description="Draft article text to audit")
    draft_text: Optional[str] = Field(None, description="Alias for draft article text")
    topic: Optional[str] = Field(None, description="Anchor topic for retrieval")
    domain_context: Optional[str] = Field(None, description="Domain context (e.g. Web Frameworks)")
    client_name: Optional[str] = Field("Client Deliverable", description="Client or project name")
    provider: Optional[str] = Field("duckduckgo", description="Search provider (duckduckgo, serpapi, mock)")
    llm_backend: Optional[str] = Field("heuristic", description="Proposition parser (heuristic, gemma)")
    decay_lambda: Optional[float] = Field(0.15, description="Freshness decay constant")
    generate_audio: Optional[bool] = Field(False, description="Whether to synthesize spoken audio briefing")
    audio_persona: Optional[str] = Field("rachel", description="Voice persona (rachel, adam, drew)")
    auto_fix: Optional[bool] = Field(True, description="Whether to compute factual repair and diff")
    engine: Optional[str] = Field("google", description="SerpApi engine (google, google_scholar, google_news)")


class FetchUrlRequest(BaseModel):
    url: str = Field(..., description="Webpage or documentation URL to extract")
    max_words: Optional[int] = Field(400, description="Maximum words to extract")


class AutoFixRequest(BaseModel):
    text: str = Field(..., description="Original draft text to repair")
    provider: Optional[str] = Field("duckduckgo", description="Search provider")
    llm_backend: Optional[str] = Field("heuristic", description="Proposition parser")


class ResearchRequest(BaseModel):
    topic: str = Field(..., description="Technical topic or claim to investigate")
    domain_context: Optional[str] = Field(None, description="Domain context")
    decay_lambda: Optional[float] = Field(0.15, description="Freshness decay constant")
    provider: Optional[str] = Field("duckduckgo", description="Search provider")


class CompareRequest(BaseModel):
    tech_a: str = Field(..., description="First technology stack")
    tech_b: str = Field(..., description="Second technology stack")
    domain_context: Optional[str] = Field(None, description="Domain context")
    provider: Optional[str] = Field("duckduckgo", description="Search provider")


class ChatFactCheckRequest(BaseModel):
    prompt: Optional[str] = Field(None, description="User factual inquiry or claim to verify")
    query: Optional[str] = Field(None, description="Alias for prompt")
    provider: Optional[str] = Field("duckduckgo", description="Search provider")
    llm_backend: Optional[str] = Field("heuristic", description="Proposition parser")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Healthcheck endpoint for Render and Docker."""
    return {
        "status": "healthy",
        "service": "ARGUS PRISM API",
        "version": "0.1.0",
        "sentry_active": SentryTracer.is_enabled(),
    }


@app.post("/api/fetch-url")
def fetch_url(req: FetchUrlRequest) -> Dict[str, Any]:
    """Extract clean text, title, and metadata from a live webpage or documentation URL."""
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    data = WebpageAuditor.fetch_url_content(req.url, max_words=req.max_words or 400)
    return data


@app.post("/api/validate")
def validate_draft(req: ValidateRequest) -> Dict[str, Any]:
    """Decompose draft propositions, audit against evidence streams, and generate client deliverables."""
    input_text = (req.text or req.draft_text or "").strip()
    if not input_text:
        raise HTTPException(status_code=400, detail="Draft text cannot be empty.")

    provider = get_provider(req.provider or "duckduckgo", fallback_to_mock=True)
    evaluator = ResearchEvaluator(provider=provider, default_lambda=req.decay_lambda)

    report = evaluator.validate_response(
        response_text=input_text,
        topic=req.topic,
        domain_context=req.domain_context,
        decay_lambda=req.decay_lambda,
        llm_backend=req.llm_backend,
        engine=getattr(req, "engine", "google"),
    )

    client_name = req.client_name or "Client Deliverable"
    roi = AuditReportGenerator.calculate_freelancer_roi(report)
    html_dossier = evaluator.generate_audit_dossier(report, client_name=client_name, project_title=req.topic or "Factual Verification Audit")
    markdown_briefing = evaluator.generate_audit_markdown(report, client_name=client_name)

    # Compute Factual Auto-Repair and In-line Diff
    auto_fix_data: Optional[Dict[str, Any]] = None
    if req.auto_fix:
        auto_fix_data = FactualAutoFixer.repair_document(input_text, report)

    # Compute Academic Markdown with Footnotes & Bibliography
    academic_data = AcademicExporter.export_publication_markdown(
        text=auto_fix_data["repaired_text"] if auto_fix_data and auto_fix_data.get("repaired_text") else input_text,
        report=report,
        style="ieee",
        author_or_client=client_name,
    )

    # Compute Dynamic Verification Badges
    badge_svg_url = f"/api/badge?score={report.overall_validity_score:.1f}&verdict={report.verdict.value}"
    badge_markdown = BadgeGenerator.generate_markdown_snippet(score=report.overall_validity_score, verdict=report.verdict.value)
    badge_html = BadgeGenerator.generate_html_snippet(score=report.overall_validity_score, verdict=report.verdict.value)

    audio_script: Optional[str] = None
    if req.generate_audio:
        try:
            audio_bytes, mime, script = evaluator.generate_audio_briefing(
                report,
                topic_or_client=client_name,
                voice_id=req.audio_persona or "rachel",
            )
            audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
            audio_script = script
        except Exception as e:
            logger.warning("Failed to generate audio in API (%s)", e)

    return {
        "report": report.model_dump(mode="json"),
        "roi": roi,
        "html_certificate": html_dossier,
        "markdown_briefing": markdown_briefing,
        "academic_markdown": academic_data["formatted_markdown"],
        "academic_footnotes_count": academic_data["footnotes_count"],
        "academic_bibliography": academic_data["bibliography"],
        "badge_svg_url": badge_svg_url,
        "badge_markdown": badge_markdown,
        "badge_html": badge_html,
        "bayesian_confidence_interval": report.bayesian_confidence_interval,
        "bayesian_distribution": report.bayesian_distribution,
        "model_consensus": report.model_consensus,
        "audio_base64": audio_base64,
        "audio_script": audio_script,
        "auto_fix": auto_fix_data,
        "repaired_text": auto_fix_data["repaired_text"] if auto_fix_data else None,
        "diff_blocks": auto_fix_data["diff_blocks"] if auto_fix_data else [],
        "fixes_count": auto_fix_data["fixes_count"] if auto_fix_data else 0,
    }


@app.get("/api/badge")
def get_verification_badge(
    score: Optional[float] = 92.0,
    verdict: Optional[str] = "FACTUALLY_SOUND",
    label: Optional[str] = "ARGUS PRISM",
) -> Response:
    """Generate dynamic SVG verification badge for GitHub READMEs, Notion, and technical articles."""
    svg_content = BadgeGenerator.generate_svg(
        score=score if score is not None else 92.0,
        verdict=verdict or "FACTUALLY_SOUND",
        left_label=label or "ARGUS PRISM",
    )
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=120",
            "Content-Security-Policy": "default-src 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )


class CompareModelsRequest(BaseModel):
    text: str = Field(..., description="Draft text to evaluate across open-weight models")
    models: Optional[List[str]] = Field(None, description="Open-weight models to compare")


@app.post("/api/compare-models")
def compare_open_weight_models(req: CompareModelsRequest) -> Dict[str, Any]:
    """Stateless open-weight multi-model consensus via Backboard API."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    from argus.llm.backboard_client import BackboardClient
    client = BackboardClient()
    return client.compare_open_weight_models(text=req.text, models=req.models)


class BayesianEvaluateRequest(BaseModel):
    tier_weight: Optional[float] = Field(1.0, description="Source tier weight")
    age_months: Optional[float] = Field(0.0, description="Source age in months")
    corroboration_count: Optional[int] = Field(1, description="Number of agreeing sources")
    conflict_count: Optional[int] = Field(0, description="Number of conflicting sources")
    base_score: Optional[float] = Field(90.0, description="Base heuristic score")


@app.post("/api/bayesian-evaluate")
def evaluate_bayesian_tabpfn(req: BayesianEvaluateRequest) -> Dict[str, Any]:
    """In-memory TabPFN Bayesian credibility and uncertainty evaluation."""
    from argus.engine.tabpfn_oracle import TabPFNOracle
    return TabPFNOracle.evaluate_claim(
        tier_weight=req.tier_weight or 1.0,
        age_months=req.age_months or 0.0,
        corroboration_count=req.corroboration_count or 1,
        conflict_count=req.conflict_count or 0,
        base_score=req.base_score or 90.0,
    )


class ExportFootnotesRequest(BaseModel):
    text: str = Field(..., description="Article text")
    style: Optional[str] = Field("ieee", description="Citation style (ieee, apa)")
    topic: Optional[str] = Field(None, description="Article topic")
    provider: Optional[str] = Field("duckduckgo", description="Search provider")
    llm_backend: Optional[str] = Field("heuristic", description="Proposition parser")


@app.post("/api/export-footnotes")
def export_footnotes(req: ExportFootnotesRequest) -> Dict[str, Any]:
    """Export article as publication-ready markdown with numerical footnotes and bibliography."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    provider = get_provider(req.provider or "duckduckgo", fallback_to_mock=True)
    evaluator = ResearchEvaluator(provider=provider)
    report = evaluator.validate_response(response_text=req.text, topic=req.topic, llm_backend=req.llm_backend)
    result = AcademicExporter.export_publication_markdown(req.text, report, style=req.style or "ieee")
    return result


@app.post("/api/auto-fix")
def auto_fix_draft(req: AutoFixRequest) -> Dict[str, Any]:
    """Autonomous factual remediation on a technical draft."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    provider = get_provider(req.provider or "duckduckgo", fallback_to_mock=True)
    evaluator = ResearchEvaluator(provider=provider)
    report = evaluator.validate_response(response_text=req.text, llm_backend=req.llm_backend)
    fix_data = FactualAutoFixer.repair_document(req.text, report)

    return {
        "report": report.model_dump(mode="json"),
        **fix_data,
    }


@app.post("/api/research")
def execute_research(req: ResearchRequest) -> Dict[str, Any]:
    """Execute full adversarial multi-vector research workflow on a topic."""
    provider = get_provider(req.provider or "duckduckgo", fallback_to_mock=True)
    evaluator = ResearchEvaluator(provider=provider, default_lambda=req.decay_lambda)
    report = evaluator.execute_research(
        topic=req.topic,
        domain_context=req.domain_context,
        decay_lambda=req.decay_lambda,
    )
    dossier = evaluator.generate_dossier(topic=req.topic)
    return {
        "report": report.model_dump(mode="json"),
        "html_dossier": dossier,
    }


@app.post("/api/compare")
def compare_technologies(req: CompareRequest) -> Dict[str, Any]:
    """Empirical head-to-head comparison between Tech A and Tech B."""
    provider = get_provider(req.provider or "duckduckgo", fallback_to_mock=True)
    evaluator = ResearchEvaluator(provider=provider)
    comp_report = evaluator.compare_technologies(
        tech_a=req.tech_a,
        tech_b=req.tech_b,
        domain_context=req.domain_context,
    )
    return {"comparison": comp_report.model_dump(mode="json")}


@app.post("/api/chat")
def chat_fact_check(req: ChatFactCheckRequest) -> Dict[str, Any]:
    """Conversational fact-checker endpoint with instant verified citations."""
    query_text = (req.prompt or req.query or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    provider = get_provider(req.provider or "duckduckgo", fallback_to_mock=True)
    evaluator = ResearchEvaluator(provider=provider)

    rep = evaluator.validate_response(
        response_text=query_text,
        llm_backend=req.llm_backend,
    )

    if rep.verdict == ValidationVerdict.FACTUALLY_SOUND:
        badge = "FACTUALLY SOUND"
        badge_color = "emerald"
    elif rep.verdict == ValidationVerdict.PARTIALLY_CONTESTED:
        badge = "PARTIALLY CONTESTED"
        badge_color = "amber"
    else:
        badge = "HIGH HALLUCINATION RISK"
        badge_color = "rose"

    citations = [
        {"url": str(c.url), "snippet": c.snippet, "tier_weight": c.tier_weight}
        for p in rep.validated_propositions
        for c in p.citations
    ][:4]

    return {
        "prompt": query_text,
        "verdict": badge,
        "verdict_color": badge_color,
        "summary": rep.summary,
        "validity_score": rep.overall_validity_score,
        "propositions": [p.model_dump(mode="json") for p in rep.validated_propositions],
        "citations": citations,
    }


@app.get("/api/telemetry")
def get_telemetry() -> Dict[str, Any]:
    """Retrieve Cost-Guard cache economics and Sentry distributed tracing status."""
    cache = SerpApiCache()
    telem = cache.get_telemetry()
    return {
        "cost_guard": telem.model_dump(),
        "sentry": {
            "is_enabled": SentryTracer.is_enabled(),
            "status": "active" if SentryTracer.is_enabled() else "local_fallback",
        },
    }
