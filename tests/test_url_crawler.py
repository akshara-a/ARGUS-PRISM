"""Tests for WebpageAuditor URL extraction and resilient fallback."""

from argus.engine.url_crawler import WebpageAuditor


def test_fetch_url_mock_cache():
    result = WebpageAuditor.fetch_url_content("https://fastapi.tiangolo.com/tutorial")

    assert "FastAPI" in result["title"]
    assert "FastAPI async endpoints achieve high throughput" in result["content"]
    assert result["word_count"] > 10
    assert result["is_live"] is False


def test_fetch_url_with_legacy_mock():
    result = WebpageAuditor.fetch_url_content("https://example.com/legacyapi/docs")

    assert "LegacyAPI" in result["title"]
    assert "LegacyAPI v1 is production ready" in result["content"]
    assert result["word_count"] > 10


def test_fetch_url_fallback_on_invalid():
    result = WebpageAuditor.fetch_url_content("https://invalid-nonexistent-domain-999.xyz/guide")

    assert "invalid-nonexistent-domain-999.xyz" in result["title"]
    assert result["word_count"] > 5
    assert result["is_live"] is False


def test_fetch_url_ssrf_blocked():
    """Verify SSRF protection blocks private IP ranges and localhost."""
    # Test localhost
    res_local = WebpageAuditor.fetch_url_content("http://127.0.0.1:8000/internal-admin")
    assert "Blocked URL" in res_local["title"]
    assert res_local["source"] == "SSRF Security Filter"
    assert res_local["is_live"] is False

    # Test cloud metadata service (AWS/GCP IMDS)
    res_meta = WebpageAuditor.fetch_url_content("http://169.254.169.254/latest/meta-data/")
    assert "Blocked URL" in res_meta["title"]
    assert res_meta["source"] == "SSRF Security Filter"

    # Test private subnet IP (192.168.1.1)
    res_private = WebpageAuditor.fetch_url_content("http://192.168.1.1/router-login")
    assert "Blocked URL" in res_private["title"]
    assert res_private["source"] == "SSRF Security Filter"

