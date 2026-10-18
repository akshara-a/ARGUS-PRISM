"""Tests for Sentry Agent Tracing & Observability Layer."""

import pytest
from unittest.mock import MagicMock, patch
from argus.observability.sentry_tracer import SentryTracer
from argus.engine.evaluator import ResearchEvaluator
from argus.engine.validator import ResponseValidator
from argus.providers.mock_provider import MockSearchStrategy


class TestSentryTracer:
    """Validate SentryTracer both in fallback (offline/no DSN) mode and active SDK mode."""

    def setup_method(self):
        # Reset SentryTracer internal state before each test
        SentryTracer._initialized = False
        SentryTracer._is_enabled = False

    def test_local_fallback_when_no_dsn(self):
        """When SENTRY_DSN is empty, tracer runs in safe local mode without errors."""
        with patch.dict("os.environ", {"SENTRY_DSN": ""}, clear=False):
            enabled = SentryTracer.init_tracer(dsn="")
            assert enabled is False
            assert SentryTracer.is_enabled() is False

    def test_trace_span_local_fallback_execution(self):
        """trace_span context manager measures execution timing in local fallback mode."""
        SentryTracer._initialized = True
        SentryTracer._is_enabled = False

        data_payload = {"phase": "planning", "query_count": 3}
        with SentryTracer.trace_span("agent.test_op", "Test operation", data=data_payload) as span:
            assert span["op"] == "agent.test_op"
            assert span["description"] == "Test operation"
            assert span["data"]["phase"] == "planning"

        assert "elapsed_ms" in span
        assert span["elapsed_ms"] >= 0.0

    def test_record_breadcrumbs_safe_in_fallback_mode(self):
        """Breadcrumbs, conflict resolutions, and Cost-Guard telemetry do not raise exceptions when Sentry is disabled."""
        SentryTracer._initialized = True
        SentryTracer._is_enabled = False

        # Should execute silently with zero exceptions
        SentryTracer.record_breadcrumb("category.test", "Test breadcrumb message")
        SentryTracer.record_conflict_resolution(
            topic="Test Topic",
            severity="HIGH",
            claim_a="Claim Alpha",
            claim_b="Claim Beta",
            resolution_notes="Disambiguated via timestamp freshness",
        )
        SentryTracer.record_cost_guard_metrics(
            total_searches=10,
            cache_hits=4,
            cost_saved_usd=0.04,
            provider_name="duckduckgo",
        )

    @patch("argus.observability.sentry_tracer.sentry_sdk")
    @patch("argus.observability.sentry_tracer.SENTRY_AVAILABLE", True)
    def test_sentry_init_active_mode(self, mock_sentry):
        """When a valid DSN is provided and sentry_sdk is present, SDK initializes and sets tags."""
        fake_dsn = "https://public@sentry.example.com/12345"
        enabled = SentryTracer.init_tracer(dsn=fake_dsn, environment="staging", sample_rate=0.8)

        assert enabled is True
        assert SentryTracer.is_enabled() is True
        mock_sentry.init.assert_called_once()
        _, kwargs = mock_sentry.init.call_args
        assert kwargs["dsn"] == fake_dsn
        assert kwargs["environment"] == "staging"
        assert kwargs["traces_sample_rate"] == 0.8
        assert kwargs["send_default_pii"] is False
        mock_sentry.set_tag.assert_any_call("app.name", "argus-prism")
        mock_sentry.set_tag.assert_any_call("agent.version", "0.1.0")

    @patch("argus.observability.sentry_tracer.sentry_sdk")
    @patch("argus.observability.sentry_tracer.SENTRY_AVAILABLE", True)
    def test_trace_span_active_mode(self, mock_sentry):
        """Active trace span delegates to sentry_sdk.start_span and populates data tags."""
        SentryTracer._initialized = True
        SentryTracer._is_enabled = True

        mock_span = MagicMock()
        mock_sentry.start_span.return_value.__enter__.return_value = mock_span

        with SentryTracer.trace_span("agent.eval", "Evaluate claims", data={"claims_count": 5}) as span:
            assert span == mock_span

        mock_sentry.start_span.assert_called_once_with(op="agent.eval", description="Evaluate claims")
        mock_span.set_data.assert_any_call("claims_count", 5)

    @patch("argus.observability.sentry_tracer.sentry_sdk")
    @patch("argus.observability.sentry_tracer.SENTRY_AVAILABLE", True)
    def test_trace_span_captures_exception(self, mock_sentry):
        """Trace span records internal_error status and captures exception when span body raises."""
        SentryTracer._initialized = True
        SentryTracer._is_enabled = True

        mock_span = MagicMock()
        mock_sentry.start_span.return_value.__enter__.return_value = mock_span

        with pytest.raises(ValueError, match="Synthetic failure"):
            with SentryTracer.trace_span("agent.failing_op", "Failing task"):
                raise ValueError("Synthetic failure")

        mock_span.set_status.assert_called_once_with("internal_error")
        mock_sentry.capture_exception.assert_called_once()

    @patch("argus.observability.sentry_tracer.sentry_sdk")
    @patch("argus.observability.sentry_tracer.SENTRY_AVAILABLE", True)
    def test_record_conflict_resolution_and_cost_guard_active(self, mock_sentry):
        """Conflict resolution and Cost-Guard telemetry register breadcrumbs and Sentry context."""
        SentryTracer._initialized = True
        SentryTracer._is_enabled = True

        SentryTracer.record_conflict_resolution(
            topic="Next.js App Router",
            severity="HIGH",
            claim_a="Requires pages directory",
            claim_b="Uses app directory in 14.0",
            resolution_notes="Resolved via freshness timestamp",
        )
        mock_sentry.add_breadcrumb.assert_called_once()
        _, bkwargs = mock_sentry.add_breadcrumb.call_args
        assert bkwargs["category"] == "agent.tie_breaker"
        assert bkwargs["level"] == "warning"

        SentryTracer.record_cost_guard_metrics(
            total_searches=20,
            cache_hits=12,
            cost_saved_usd=0.12,
            provider_name="duckduckgo",
        )
        mock_sentry.set_tag.assert_called_with("cost_guard.provider", "duckduckgo")
        mock_sentry.set_context.assert_called_once()
        cargs, _ = mock_sentry.set_context.call_args
        assert cargs[0] == "cost_guard_telemetry"
        assert cargs[1]["cost_saved_usd"] == 0.12

    def test_evaluator_and_validator_integration_with_tracer(self):
        """ResearchEvaluator and ResponseValidator run seamlessly with Sentry tracing enabled/disabled."""
        evaluator = ResearchEvaluator(provider=MockSearchStrategy())
        validator = ResponseValidator(evaluator=evaluator)

        report = validator.validate(
            response_text="React 19 was officially released in December 2024 with Server Actions.",
            topic="React 19 release date",
        )
        assert report is not None
        assert report.total_claims_evaluated >= 1
