"""Tests for AuditReportGenerator and Freelancer Side-Hustle ROI."""

from argus.engine.audit_report import AuditReportGenerator
from argus.engine.evaluator import ResearchEvaluator
from argus.models.domain import NodeState, ValidatedClaim, ValidationReport, ValidationVerdict
from argus.providers import MockSearchStrategy


def test_calculate_freelancer_roi():
    report = ValidationReport(
        original_text="FastAPI async endpoints achieve high throughput using AnyIO concurrency, running on Uvicorn.",
        overall_validity_score=95.0,
        verdict=ValidationVerdict.FACTUALLY_SOUND,
        summary="All propositions verified.",
        validated_propositions=[
            ValidatedClaim(
                proposition_text="FastAPI async endpoints achieve high throughput",
                status=NodeState.VERIFIED,
                confidence_score=95.0,
            ),
            ValidatedClaim(
                proposition_text="FastAPI uses AnyIO concurrency",
                status=NodeState.VERIFIED,
                confidence_score=92.0,
            ),
        ],
        total_claims_evaluated=2,
        verified_count=2,
    )

    roi = AuditReportGenerator.calculate_freelancer_roi(report, hourly_rate_usd=50.0)
    assert roi["propositions_evaluated"] == 2
    assert roi["estimated_hours_saved"] >= 0.5
    assert roi["billable_value_usd"] > 0
    assert roi["compute_cost_usd"] == 0.0
    assert roi["profit_margin_pct"] == 100.0


def test_generate_html_dossier():
    report = ValidationReport(
        original_text="LegacyAPI v1 is production ready with guaranteed thread safety for high concurrency systems.",
        overall_validity_score=15.0,
        verdict=ValidationVerdict.HIGH_HALLUCINATION_RISK,
        summary="High risk: contains deprecated assertions.",
        validated_propositions=[
            ValidatedClaim(
                proposition_text="LegacyAPI v1 is production ready",
                status=NodeState.REFUTED,
                confidence_score=10.0,
                contradiction_warning="Overruled by official changelog deprecation notice.",
                suggested_correction="Migrate to v2 immediately.",
            )
        ],
        total_claims_evaluated=1,
        refuted_count=1,
    )

    html_out = AuditReportGenerator.generate_html_dossier(
        report=report,
        client_name="FinTech Corp Due Diligence",
        project_title="LegacyAPI Assessment",
    )
    assert "<!DOCTYPE html>" in html_out
    assert "FinTech Corp Due Diligence" in html_out
    assert "HIGH HALLUCINATION RISK" in html_out
    assert "Freelance Economics &amp; Audit Value Savings" in html_out or "Freelance Economics & Audit Value Savings" in html_out
    assert "Migrate to v2 immediately." in html_out


def test_generate_markdown_briefing():
    report = ValidationReport(
        original_text="QuantumReactJS provides zero-latency reactivity.",
        overall_validity_score=0.0,
        verdict=ValidationVerdict.HIGH_HALLUCINATION_RISK,
        summary="Zero empirical evidence found in authoritative sources.",
        validated_propositions=[],
        total_claims_evaluated=0,
    )

    md_out = AuditReportGenerator.generate_markdown_briefing(report, client_name="Acme Inc")
    assert "# 🛡️ Fact-Checking Audit Briefing: Acme Inc" in md_out
    assert "Commercial ROI & Efficiency Summary" in md_out
    assert "Overall Integrity Score:" in md_out


def test_evaluator_audit_dossier_facade():
    evaluator = ResearchEvaluator(provider=MockSearchStrategy())
    report = evaluator.validate_response("FastAPI async endpoints achieve high throughput.")
    dossier_html = evaluator.generate_audit_dossier(report, client_name="Demo Test")
    assert "<!DOCTYPE html>" in dossier_html
    assert "Demo Test" in dossier_html
