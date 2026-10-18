"""Unit tests for Cost-Guard Dual-Tier Telemetry Cache (LRU + SQLite)."""

import os
import tempfile
import pytest
from datetime import datetime, timezone
from argus.models.domain import RawDocument
from argus.providers.cache import SerpApiCache


def test_cache_memory_and_sqlite_tier():
    """Verify tier 1 memory LRU and tier 2 SQLite hit behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = SerpApiCache(cache_dir=tmpdir, memory_capacity=2)

        doc = RawDocument(
            doc_id="test_doc_1",
            title="Test Document",
            snippet="Testing cache storage snippet",
            url="https://example.com/test",
            source_domain="example.com",
            published_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        # 1. Miss initially
        miss = cache.get("test query", engine="google", num=5)
        assert miss is None
        assert cache.total_searches == 1
        assert cache.live_api_calls == 1

        # 2. Put into cache
        cache.put("test query", [doc], engine="google", num=5)

        # 3. Hit from Tier 1 (Memory)
        hit_mem = cache.get("test query", engine="google", num=5)
        assert hit_mem is not None
        assert len(hit_mem) == 1
        assert hit_mem[0].title == "Test Document"
        assert cache.cache_hits == 1

        # 4. Fill memory to force LRU eviction into Tier 2 (SQLite)
        doc2 = doc.model_copy(update={"doc_id": "test_doc_2"})
        doc3 = doc.model_copy(update={"doc_id": "test_doc_3"})
        cache.put("query 2", [doc2], engine="google", num=5)
        cache.put("query 3", [doc3], engine="google", num=5)

        # "test query" should now be evicted from memory cache and retrieved from SQLite tier
        hit_db = cache.get("test query", engine="google", num=5)
        assert hit_db is not None
        assert len(hit_db) == 1
        assert hit_db[0].title == "Test Document"
        assert cache.cache_hits == 2


def test_cache_persistence_across_instances():
    """Verify data persisted in SQLite is accessible across separate cache instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache1 = SerpApiCache(cache_dir=tmpdir)
        doc = RawDocument(
            doc_id="doc_persist",
            title="Persistent Doc",
            snippet="Testing cross-instance persistence",
            url="https://example.com/persist",
            source_domain="example.com",
        )
        cache1.put("persist query", [doc])

        # Spin up fresh cache instance pointing to same directory
        cache2 = SerpApiCache(cache_dir=tmpdir)
        # Memory is empty in new instance, must retrieve from SQLite
        retrieved = cache2.get("persist query")
        assert retrieved is not None
        assert len(retrieved) == 1
        assert retrieved[0].title == "Persistent Doc"


def test_cache_telemetry_metrics():
    """Verify Cost-Guard economics calculations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = SerpApiCache(cache_dir=tmpdir, cost_per_query_usd=0.01)

        # Perform 4 queries: 2 misses, 2 hits
        cache.get("q1")  # miss
        cache.put("q1", [])
        cache.get("q1")  # hit

        cache.get("q2")  # miss
        cache.put("q2", [])
        cache.get("q2")  # hit

        telemetry = cache.get_telemetry()
        assert telemetry.total_searches == 4
        assert telemetry.cache_hits == 2
        assert telemetry.live_api_calls == 2
        assert telemetry.cache_hit_rate_pct == 50.0
        assert telemetry.estimated_cost_saved_usd == 0.02
        assert telemetry.avg_latency_ms > 0.0


def test_cache_clear():
    """Verify clear flushes memory and database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = SerpApiCache(cache_dir=tmpdir)
        doc = RawDocument(
            doc_id="doc_clear",
            title="Clear Doc",
            snippet="Clear snippet",
            url="https://example.com/clear",
            source_domain="example.com",
        )
        cache.put("clear query", [doc])
        cache.clear()

        assert cache.get("clear query") is None
