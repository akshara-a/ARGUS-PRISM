"""Unit tests for Backboard open-weight multi-model consensus router."""

from argus.llm.backboard_client import BackboardClient


def test_backboard_initialization():
    """Verify Backboard client initializes with defaults and respects configuration."""
    client = BackboardClient(api_key="test_dummy_key_12345")
    assert client.api_key == "test_dummy_key_12345"
    assert client.is_live_configured() is True
    assert len(client.OPEN_WEIGHT_MODELS) == 3


def test_backboard_compare_empty_text():
    """Verify handling of empty or blank text input."""
    client = BackboardClient()
    res = client.compare_open_weight_models("")
    assert res["zero_persistence"] is True
    assert res["propositions"] == []
    assert res["consensus_score"] == 0.0
    assert res["agreement_ratio"] == "0/0"


def test_backboard_compare_valid_text():
    """Verify stateless consensus simulation on standard technical text."""
    client = BackboardClient()
    text = "FastAPI uses Pydantic for validation and runs on ASGI servers like Uvicorn."
    res = client.compare_open_weight_models(text)

    assert res["zero_persistence"] is True
    assert len(res["propositions"]) > 0
    assert res["consensus_score"] >= 0.80
    assert res["agreement_ratio"] == "3/3 Models Concur"
    assert "model_breakdown" in res
    assert len(res["model_breakdown"]) == 3
    for model_name, info in res["model_breakdown"].items():
        assert info["verdict"] == "FACTUALLY_SOUND"
        assert info["confidence"] >= 0.85


def test_backboard_compare_hallucinated_text():
    """Verify open-weight models flag hallucinated packages in consensus."""
    client = BackboardClient()
    text = "QuantumReactJS is a cutting edge quantum state framework."
    res = client.compare_open_weight_models(text)

    assert res["zero_persistence"] is True
    assert res["consensus_score"] <= 0.20
    for model_name, info in res["model_breakdown"].items():
        assert info["verdict"] == "HIGH_HALLUCINATION_RISK"
        assert "QuantumReactJS" in info["flagged_tokens"]


def test_backboard_extract_claims():
    """Verify extract_claims returns atomic propositions without side effects."""
    client = BackboardClient()
    text = "FastAPI is fast. Python 3.12 introduces improvements to the GIL."
    claims = client.extract_claims(text)
    assert isinstance(claims, list)
    assert len(claims) >= 1
