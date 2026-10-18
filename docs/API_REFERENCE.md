# ARGUS PRISM: Complete API & Protocol Reference

ARGUS PRISM exposes dual developer interfaces:
1. **FastAPI REST Server** ([`backend/src/argus/api/server.py`](../backend/src/argus/api/server.py)) — High-throughput JSON endpoints powering the Next.js 16 Web Studio, dynamic SVG badge embeds, and external microservices.
2. **Model Context Protocol (MCP 2.x) Server** ([`backend/src/argus/mcp/server.py`](../backend/src/argus/mcp/server.py)) — Native stdio/SSE agentic protocol exposing **15 deterministic tools**, resources, and prompt templates to AI agents (Claude Desktop, Cursor, Antigravity, Gemini CLI).

---

## 🌐 1. FastAPI REST Endpoints

* **Base URL (Local)**: `http://localhost:8000`
* **Base URL (Production / Render)**: `https://<your-service>.onrender.com`
* **Interactive OpenAPI UI**: `http://localhost:8000/docs`
* **CORS**: Configured dynamically via `CORS_ALLOWED_ORIGINS` and `CORS_ORIGIN_REGEX`.

---

### 1.1 `GET /api/health`
Checks server health, core engine status, and Sentry distributed tracing state.

**Request:**
```bash
curl -X GET http://localhost:8000/api/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "ARGUS PRISM API",
  "version": "0.1.0",
  "sentry_active": true
}
```

---

### 1.2 `POST /api/validate`
The primary verification endpoint. Decomposes draft text into atomic propositions, audits them against multi-vector live search streams, calculates TabPFN Bayesian uncertainty bounds ($\pm\sigma\%$), computes factual auto-repairs with git diffs, synthesizes optional spoken audio debriefs, and returns client deliverables.

**Request Body (`ValidateRequest`):**
```json
{
  "text": "FastAPI async endpoints achieve high throughput using AnyIO concurrency, running on Uvicorn.",
  "topic": "FastAPI async performance",
  "domain_context": "Web Services",
  "client_name": "Acme Ghostwriting",
  "provider": "duckduckgo",
  "llm_backend": "heuristic",
  "decay_lambda": 0.15,
  "generate_audio": true,
  "audio_persona": "rachel",
  "auto_fix": true,
  "engine": "google"
}
```

**Response (200 OK):**
```json
{
  "report": {
    "topic": "FastAPI async performance",
    "overall_validity_score": 93.8,
    "verdict": "FACTUALLY_SOUND",
    "summary": "All extracted propositions are corroborated by fresh Tier 1 documentation.",
    "total_claims_evaluated": 2,
    "verified_count": 2,
    "contested_count": 0,
    "refuted_count": 0,
    "weak_count": 0,
    "validated_propositions": [
      {
        "proposition_text": "FastAPI async endpoints achieve high throughput using AnyIO concurrency.",
        "status": "VERIFIED",
        "confidence_score": 94.0,
        "contradiction_warning": null,
        "suggested_correction": null,
        "citations": [
          {
            "url": "https://fastapi.tiangolo.com/async/",
            "tier_weight": 1.0,
            "snippet": "FastAPI supports concurrency and async endpoints out of the box via AnyIO on ASGI."
          }
        ]
      }
    ]
  },
  "roi": {
    "estimated_hours_saved": 1.2,
    "billable_value_usd": 60.0,
    "hourly_rate_usd": 50.0,
    "turnaround_time_seconds": 1.45
  },
  "html_certificate": "<!DOCTYPE html><html>...</html>",
  "markdown_briefing": "# ARGUS PRISM Factual Audit...",
  "academic_markdown": "# FastAPI async performance[^1]...",
  "academic_footnotes_count": 2,
  "academic_bibliography": "[^1]: FastAPI Documentation. https://fastapi.tiangolo.com/async/",
  "badge_svg_url": "/api/badge?score=93.8&verdict=FACTUALLY_SOUND",
  "badge_markdown": "[![ARGUS PRISM](http://localhost:8000/api/badge?score=93.8&verdict=FACTUALLY_SOUND)](http://localhost:8000)",
  "badge_html": "<a href=\"http://localhost:8000\"><img src=\"http://localhost:8000/api/badge?score=93.8&verdict=FACTUALLY_SOUND\" alt=\"ARGUS PRISM Badge\" /></a>",
  "bayesian_confidence_interval": [90.5, 96.2],
  "bayesian_distribution": {"verified_prob": 0.94, "contested_prob": 0.04, "refuted_prob": 0.02},
  "model_consensus": {"agreement_score": 96.0, "models_tested": ["llama3", "mistral", "gemma2"]},
  "audio_base64": "UklGRi...",
  "audio_script": "Executive Evidence Briefing: All propositions have been corroborated...",
  "auto_fix": {
    "fixes_count": 0,
    "repaired_text": "FastAPI async endpoints achieve high throughput using AnyIO concurrency, running on Uvicorn.",
    "diff_blocks": []
  },
  "repaired_text": "FastAPI async endpoints achieve high throughput using AnyIO concurrency, running on Uvicorn.",
  "diff_blocks": [],
  "fixes_count": 0
}
```

---

### 1.3 `POST /api/auto-fix`
Synthesizes factual remediation on a technical draft without needing a full audit payload, returning unified git-style inline diffs (`-` / `+`).

**Request Body (`AutoFixRequest`):**
```json
{
  "text": "Python 3.12 was released in the year 1999.",
  "provider": "duckduckgo",
  "llm_backend": "heuristic"
}
```

**Response (200 OK):**
```json
{
  "original_text": "Python 3.12 was released in the year 1999.",
  "repaired_text": "Python 3.12 was released in October 2023.",
  "fixes_count": 1,
  "diff_blocks": [
    {
      "original": "Python 3.12 was released in the year 1999.",
      "repaired": "Python 3.12 was released in October 2023.",
      "reason": "Corrected release date based on official Python 3.12 release notes."
    }
  ],
  "report": { ... }
}
```

---

### 1.4 `POST /api/fetch-url`
Safely scrapes and extracts clean text, title, and metadata from live documentation or technical webpages, protected by SSRF defenses (blocks RFC 1918/3927 private IPs, loopbacks, and non-HTTP protocols).

**Request Body (`FetchUrlRequest`):**
```json
{
  "url": "https://fastapi.tiangolo.com/async/",
  "max_words": 400
}
```

**Response (200 OK):**
```json
{
  "url": "https://fastapi.tiangolo.com/async/",
  "title": "Concurrency and async / await - FastAPI",
  "content": "If you are using third party libraries that tell you to call them with await...",
  "word_count": 384
}
```

---

### 1.5 `GET /api/badge`
Generates a dynamic, shields.io-compatible SVG verification badge suitable for embedding directly in GitHub READMEs, Notion pages, and technical documentation.

**Query Parameters:**
* `score` *(float, default: 92.0)*: The validity score (0–100).
* `verdict` *(string, default: "FACTUALLY_SOUND")*: `FACTUALLY_SOUND`, `PARTIALLY_CONTESTED`, or `HIGH_HALLUCINATION_RISK`.
* `label` *(string, default: "ARGUS PRISM")*: Left label text.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/badge?score=94.5&verdict=FACTUALLY_SOUND"
```

**Response (200 OK):**
Content-Type: `image/svg+xml` with strict `Content-Security-Policy: default-src 'none'`.

---

### 1.6 `POST /api/compare-models`
Cross-examines a technical draft across open-weight models (**Llama 3 + Mistral + Gemma 2**) using Backboard multi-model routing in volatile RAM with zero prompt persistence.

**Request Body (`CompareModelsRequest`):**
```json
{
  "text": "React 19 removes forwardRef in favor of passing ref as a normal prop.",
  "models": ["llama-3-8b-instruct", "mistral-7b-instruct", "gemma-2-9b-it"]
}
```

**Response (200 OK):**
```json
{
  "consensus_reached": true,
  "consensus_verdict": "VERIFIED",
  "model_evaluations": {
    "llama-3-8b-instruct": {"verdict": "VERIFIED", "confidence": 95.0},
    "mistral-7b-instruct": {"verdict": "VERIFIED", "confidence": 92.0},
    "gemma-2-9b-it": {"verdict": "VERIFIED", "confidence": 94.0}
  },
  "divergence_score": 0.03
}
```

---

### 1.7 `POST /api/bayesian-evaluate`
Computes in-memory Bayesian credibility class probabilities and epistemic uncertainty intervals ($\pm\sigma$) using TabPFN Prior-Data Fitted Networks.

**Request Body (`BayesianEvaluateRequest`):**
```json
{
  "tier_weight": 1.0,
  "age_months": 2.0,
  "corroboration_count": 4,
  "conflict_count": 0,
  "base_score": 92.0
}
```

**Response (200 OK):**
```json
{
  "bayesian_score": 93.4,
  "uncertainty_interval": [91.0, 95.8],
  "epistemic_uncertainty_sigma": 2.4,
  "class_probabilities": {
    "verified": 0.94,
    "contested": 0.04,
    "refuted": 0.02
  }
}
```

---

### 1.8 `POST /api/export-footnotes`
Converts article text into publication-ready Markdown with numbered academic footnotes (`[^1]`, `[^2]`) and formatted IEEE or APA bibliographies based on verified live sources.

**Request Body (`ExportFootnotesRequest`):**
```json
{
  "text": "PyTorch 2.0 introduced torch.compile for graph capture and kernel fusion.",
  "style": "ieee",
  "topic": "PyTorch 2.0 Compilation"
}
```

---

### 1.9 `POST /api/research`
Orchestrates autonomous multi-vector search (optimistic, skeptical, temporal) and executes the GoF state machine verification loop on an open-ended topic.

**Request Body (`ResearchRequest`):**
```json
{
  "topic": "Python 3.13 free threading PEP 703 performance",
  "domain_context": "Python Systems Engineering",
  "decay_lambda": 0.015,
  "provider": "duckduckgo"
}
```

---

### 1.10 `POST /api/compare`
Runs head-to-head empirical technology comparison across 4 objective dimensions (Evidence Confidence, Verified Claims, Operational Stability, Ecosystem Freshness) and recommends an objective winner.

**Request Body (`CompareRequest`):**
```json
{
  "tech_a": "FastAPI",
  "tech_b": "Express.js",
  "domain_context": "Microservice Gateways",
  "provider": "duckduckgo"
}
```

---

### 1.11 `POST /api/chat`
Conversational truth assistant. Answers user technical inquiries backed strictly by deterministic evidence streams with verified citations.

**Request Body (`ChatFactCheckRequest`):**
```json
{
  "prompt": "Is Python 2.7 still supported by the Python Software Foundation?",
  "provider": "duckduckgo"
}
```

---

### 1.12 `GET /api/telemetry`
Returns live **Cost-Guard** dual-tier cache telemetry (queries processed across Tier 1 RAM LRU and Tier 2 SQLite disk, cache hit rate percentage, and cumulative USD cost savings at $0.01/query) alongside Sentry distributed tracing health.

**Request:**
```bash
curl -X GET http://localhost:8000/api/telemetry
```

**Response (200 OK):**
```json
{
  "cost_guard": {
    "total_searches": 48,
    "cache_hits": 41,
    "live_api_calls": 7,
    "cache_hit_rate_pct": 85.4,
    "estimated_cost_saved_usd": 0.41,
    "avg_latency_ms": 12.3
  },
  "sentry": {
    "is_enabled": true,
    "status": "active"
  }
}
```

---

## 🤖 2. Model Context Protocol (MCP 2.x) Tools

When launched via `argus mcp --transport stdio` or `python -m argus.mcp.server`, ARGUS PRISM exposes **15 native deterministic tools** conforming to the open Model Context Protocol:

### Connecting to Claude Desktop / Cursor IDE
Add to your `claude_desktop_config.json` or Cursor settings:
```json
{
  "mcpServers": {
    "argus-prism": {
      "command": "python",
      "args": ["-m", "argus.mcp.server"],
      "cwd": "/path/to/ARGUS-PRISM",
      "env": {
        "SEARCH_PROVIDER": "duckduckgo"
      }
    }
  }
}
```

---

### 🛠️ Complete MCP Tool Suite (15 Tools)

| Tool Name | Arguments | Output Description |
| :--- | :--- | :--- |
| **`execute_research`** | `topic: str`, `domain_context?: str`, `decay_lambda?: float` | Executes tri-vector search, credibility tiering, freshness decay, and self-correction loop. |
| **`execute_targeted_search`** | `query: str`, `search_type?: str` | Performs normalized search via adapter into `RawDocument` models. |
| **`inspect_evidence`** | `claim_id: str` | Retrieves raw search snippets, URLs, and citations associated with a specific claim finding. |
| **`inspect_confidence`** | `claim_id: str` | Returns the step-by-step mathematical breakdown for a claim's deterministic confidence score. |
| **`inspect_conflicts`** | `claim_id?: str` | Returns competing claims and opposing source URLs detected during research. |
| **`compare_technologies`** | `tech_a: str`, `tech_b: str`, `domain_context?: str` | Compares two technologies head-to-head across empirical dimensions and declares an objective winner. |
| **`inspect_telemetry`** | *None* | Returns Cost-Guard cache hit rates, query latencies, and estimated dollar savings. |
| **`generate_dossier`** | `topic?: str` | Generates a standalone print-ready HTML evidence dossier for compliance and legal audits. |
| **`validate_response`** | `response_text: str`, `topic?: str`, `decay_lambda?: float` | Audits an LLM-generated response, catching hallucinations, deprecations, and suggesting corrections. |
| **`auto_repair_draft`** | `draft_text: str`, `topic?: str`, `domain_context?: str` | Autonomously repairs factual errors in a technical draft, returning corrected text and git-style diffs. |
| **`crawl_and_audit_url`** | `url: str`, `max_words?: int` | Crawls a live webpage/docs URL (SSRF-protected), extracts text, and performs factual verification. |
| **`export_academic_markdown`** | `text: str`, `topic?: str`, `style?: str` | Exports article as publication-ready Markdown with in-line footnotes (`[^1]`) and IEEE/APA bibliography. |
| **`generate_verification_badge`** | `score: float`, `verdict?: str`, `label?: str` | Generates embeddable SVG verification badge and copyable Markdown/HTML snippets. |
| **`backboard_compare_models`** | `text: str`, `models?: List[str]` | Cross-examines a draft across open-weight models (Llama 3, Mistral, Gemma 2) via Backboard API. |
| **`tabpfn_bayesian_uncertainty`** | `tier_weight?: float`, `age_months?: float`, `corroboration_count?: int`, `conflict_count?: int`, `base_score?: float` | Computes in-memory Bayesian credibility class probabilities and epistemic uncertainty ($\pm\sigma$). |

---

### 📦 MCP Resources
* **`argus://reports/latest`**: Returns the most recent `EvidenceReport` payload as a serialized JSON string.
* **`argus://conflicts/active`**: Returns active and unresolved technical conflicts detected during the latest session.
* **`argus://reports/dossier`**: Returns standalone print-ready HTML evidence dossier.
* **`argus://graph/dot`**: Returns Graphviz DOT representation of the evidence directed acyclic graph.

---

### 💬 MCP Prompt Templates
* **`audit_draft`**: Prompts an agent to ingest a technical draft, decompose propositions, run empirical audits, and apply autonomous factual repairs.
* **`research_topic`**: Guides an agent through multi-vector evidence gathering on an emerging engineering topic.
* **`compare_stacks`**: Directs an agent to execute an empirical head-to-head architectural trade-off evaluation.
