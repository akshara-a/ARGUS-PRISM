"""Domain entities and Pydantic schemas for ARGUS PRISM."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class CredibilityTier(str, Enum):
    """Source credibility tier classification."""
    TIER_1_AUTHORITATIVE = "Tier 1 (Authoritative)"
    TIER_2_COMMUNITY = "Tier 2 (Community)"
    TIER_3_UNVERIFIED = "Tier 3 (Unverified)"


class NodeState(str, Enum):
    """Visual DAG Claim Node State."""
    VERIFIED = "VERIFIED"     # High confidence, corroborated, no active conflict
    CONTESTED = "CONTESTED"   # Conflict detected, under resolution or unresolved
    WEAK = "WEAK"             # Low score, uncorroborated or stale
    REFUTED = "REFUTED"       # Overruled by authoritative fresher evidence


class SearchVectorType(str, Enum):
    """Adversarial Query Vector types."""
    OPTIMISTIC = "optimistic"
    SKEPTIC = "skeptic"
    TEMPORAL = "temporal"
    TIE_BREAKER = "tie_breaker"
    TARGETED = "targeted"


class QueryVector(BaseModel):
    """Single query vector spawned by AdversarialQueryBuilder."""
    query_text: str
    vector_type: SearchVectorType
    rationale: str
    target_engine: str = "google"


class RawDocument(BaseModel):
    """Normalized domain entity output by ISearchProvider and SerpApiAdapter."""
    doc_id: str
    title: str
    snippet: str
    url: str
    source_domain: str
    publication_time: Optional[str] = None
    published_date: Optional[datetime] = None
    search_vector: Optional[str] = None
    engine: str = "google"
    raw_payload: Optional[Dict[str, Any]] = None


class Citation(BaseModel):
    """Verifiable citation backing or contradicting a claim."""
    url: HttpUrl
    snippet: str
    publication_time: Optional[str] = None
    tier_weight: float = Field(..., description="1.5x (Tier 1), 1.0x (Tier 2), 0.5x (Tier 3)")
    # Additional metadata for inspector and math breakdown
    tier_label: Optional[str] = None
    age_months: Optional[float] = None
    decay_multiplier: Optional[float] = None
    effective_weight: Optional[float] = None


class ScoreBreakdown(BaseModel):
    """Mathematical breakdown of deterministic confidence calculation."""
    base_score: float
    tier_weight: float
    age_months: float
    decay_lambda: float
    decay_multiplier: float
    corroboration_bonus: float
    conflict_penalty: float
    final_score: float
    formula: str
    domain_category: Optional[str] = "General"
    inferred_lambda: Optional[float] = None
    bayesian_posterior: Optional[float] = None


class Claim(BaseModel):
    """Atomic proposition evaluated mathematically."""
    claim_id: Optional[str] = None
    claim_text: str
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Deterministic confidence score (0-100)")
    supporting_citations: List[Citation] = Field(default_factory=list)
    contradicting_citations: List[Citation] = Field(default_factory=list)
    is_corroborated: bool = False
    node_state: NodeState = NodeState.WEAK
    breakdown: Optional[ScoreBreakdown] = None
    conflict_rationale: Optional[str] = None


class ConflictItem(BaseModel):
    """Explicit semantic conflict identified between claims or sources."""
    conflict_id: str
    topic: str
    claim_a: str
    claim_b: str
    source_a_url: str
    source_b_url: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    status: str    # "RESOLVED", "UNRESOLVED", "IN_PROGRESS"
    resolution_notes: Optional[str] = None


class ClaimRelationType(str, Enum):
    """Semantic relation type between claim propositions."""
    ENTAILS = "ENTAILS"
    REQUIRES = "REQUIRES"
    CONTRADICTS = "CONTRADICTS"
    TRANSITIVELY_CONTRADICTS = "TRANSITIVELY_CONTRADICTS"


class ClaimRelation(BaseModel):
    """Directed edge in the Evidence Dependency DAG."""
    source_claim_id: str
    target_claim_id: str
    relation_type: ClaimRelationType
    rationale: str
    confidence: float = 1.0


class GraphMetrics(BaseModel):
    """Topological metrics computed across the Evidence Graph."""
    contradiction_density: float = Field(..., description="Ratio of conflicting pairs to total claim pairs")
    consensus_centrality: float = Field(..., description="Average corroboration centrality (0-100)")
    total_edges: int = 0
    entailment_count: int = 0


class CostGuardTelemetry(BaseModel):
    """API economics and dual-tier cache efficiency metrics."""
    total_searches: int = 0
    cache_hits: int = 0
    live_api_calls: int = 0
    cache_hit_rate_pct: float = 0.0
    estimated_cost_saved_usd: float = 0.0
    avg_latency_ms: float = 0.0


class TradeOffDimension(BaseModel):
    """Comparative metric dimension between two evaluated technologies."""
    dimension_name: str
    tech_a_score: float
    tech_b_score: float
    winner: str
    notes: str


class EvidenceReport(BaseModel):
    """Standard Model Context Protocol payload contract."""
    composite_summary: str
    global_confidence_score: float = Field(..., ge=0.0, le=100.0)
    structured_claims: List[Claim]
    unresolved_conflicts: List[str] = Field(default_factory=list)
    total_searches_executed: int = 0
    detailed_conflicts: List[ConflictItem] = Field(default_factory=list)
    execution_time_seconds: Optional[float] = None
    query_vectors_used: List[str] = Field(default_factory=list)
    domain_category: Optional[str] = None
    inferred_lambda: Optional[float] = None
    engine_telemetry: Dict[str, int] = Field(default_factory=dict)
    relations: List[ClaimRelation] = Field(default_factory=list)
    graph_metrics: Optional[GraphMetrics] = None
    cost_guard: Optional[CostGuardTelemetry] = None


class ComparisonReport(BaseModel):
    """Head-to-head empirical technology comparison report."""
    tech_a: str
    tech_b: str
    report_a: EvidenceReport
    report_b: EvidenceReport
    trade_off_dimensions: List[TradeOffDimension] = Field(default_factory=list)
    recommended_winner: str
    verdict_rationale: str
    comparison_summary: str


class ValidationVerdict(str, Enum):
    """Overall factual integrity verdict of an evaluated LLM response."""
    FACTUALLY_SOUND = "FACTUALLY_SOUND"
    PARTIALLY_CONTESTED = "PARTIALLY_CONTESTED"
    HIGH_HALLUCINATION_RISK = "HIGH_HALLUCINATION_RISK"


class ValidatedClaim(BaseModel):
    """Individual proposition extracted from an LLM response with factual verdict."""
    proposition_text: str
    status: NodeState
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    citations: List[Citation] = Field(default_factory=list)
    contradiction_warning: Optional[str] = None
    suggested_correction: Optional[str] = None


class ValidationReport(BaseModel):
    """Empirical audit report validating an LLM-generated response or user statement."""
    original_text: str
    overall_validity_score: float = Field(..., ge=0.0, le=100.0, description="Deterministic confidence score (0-100)")
    verdict: ValidationVerdict
    summary: str
    topic: Optional[str] = None
    validated_propositions: List[ValidatedClaim] = Field(default_factory=list)
    total_claims_evaluated: int = 0
    verified_count: int = 0
    contested_count: int = 0
    refuted_count: int = 0
    weak_count: int = 0
    underlying_evidence_report: Optional[EvidenceReport] = None
    bayesian_confidence_interval: Optional[float] = None
    bayesian_distribution: Optional[Dict[str, float]] = None
    model_consensus: Optional[Dict[str, Any]] = None

