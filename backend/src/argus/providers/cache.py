"""Cost-Guard Dual-Tier Telemetry Cache (Memory LRU + Persistent SQLite)."""

import hashlib
import json
import os
import sqlite3
import time
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from argus.models.domain import CostGuardTelemetry, RawDocument


class SerpApiCache:
    """Manages dual-tier caching (in-memory LRU + SQLite) and Cost-Guard economics tracking."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl_seconds: int = 86400,  # 24 hours
        memory_capacity: int = 128,
        cost_per_query_usd: float = 0.01,
    ):
        self.default_ttl = default_ttl_seconds
        self.memory_capacity = memory_capacity
        self.cost_per_query = cost_per_query_usd

        # In-memory LRU tier
        self._memory_cache: OrderedDict[str, Tuple[List[RawDocument], float]] = OrderedDict()

        # Telemetry metrics
        self.total_searches = 0
        self.cache_hits = 0
        self.live_api_calls = 0
        self.latency_samples_ms: List[float] = []

        # SQLite persistent tier
        base_dir = Path(cache_dir) if cache_dir else Path(".cache")
        base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(base_dir / "serpapi_cache.sqlite")
        self._init_db()

    @contextmanager
    def _connection(self):
        """Context manager guaranteeing connection closure to prevent Windows file locking."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize SQLite cache schema."""
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    query TEXT,
                    engine TEXT,
                    documents_json TEXT,
                    created_at REAL,
                    expires_at REAL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON search_cache (expires_at)")
            conn.commit()

    @staticmethod
    def generate_key(
        query: str,
        engine: str = "google",
        num: int = 5,
        vector_type: Optional[str] = None,
    ) -> str:
        """Generate deterministic cache key."""
        raw = f"{query.strip().lower()}:{engine.strip().lower()}:{num}:{str(vector_type).lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self,
        query: str,
        engine: str = "google",
        num: int = 5,
        vector_type: Optional[str] = None,
    ) -> Optional[List[RawDocument]]:
        """Lookup query in memory or SQLite cache."""
        self.total_searches += 1
        key = self.generate_key(query, engine, num, vector_type=vector_type)
        now = time.time()

        # Tier 1: Check memory LRU
        if key in self._memory_cache:
            docs, expires_at = self._memory_cache[key]
            if now < expires_at:
                self._memory_cache.move_to_end(key)
                self.cache_hits += 1
                self.latency_samples_ms.append(0.5)
                return [d.model_copy() for d in docs]
            else:
                del self._memory_cache[key]

        # Tier 2: Check SQLite persistent database
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "SELECT documents_json, expires_at FROM search_cache WHERE cache_key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                if row:
                    docs_json, expires_at = row
                    if now < expires_at:
                        data = json.loads(docs_json)
                        docs = [RawDocument(**item) for item in data]
                        # Populate back into memory tier
                        self._put_memory(key, docs, expires_at)
                        self.cache_hits += 1
                        self.latency_samples_ms.append(2.0)
                        return docs
                    else:
                        conn.execute("DELETE FROM search_cache WHERE cache_key = ?", (key,))
                        conn.commit()
        except Exception:
            pass

        self.live_api_calls += 1
        return None

    def put(
        self,
        query: str,
        documents: List[RawDocument],
        engine: str = "google",
        num: int = 5,
        ttl_seconds: Optional[int] = None,
        fetch_latency_ms: float = 350.0,
        vector_type: Optional[str] = None,
    ):
        """Write search results into both cache tiers."""
        key = self.generate_key(query, engine, num, vector_type=vector_type)
        ttl = ttl_seconds or self.default_ttl
        now = time.time()
        expires_at = now + ttl

        self.latency_samples_ms.append(fetch_latency_ms)

        # Store in memory tier
        self._put_memory(key, documents, expires_at)

        # Store in SQLite tier
        try:
            serialized = json.dumps([d.model_dump(mode="json") for d in documents])
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO search_cache (cache_key, query, engine, documents_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (key, query, engine, serialized, now, expires_at),
                )
                conn.commit()
        except Exception:
            pass

    def _put_memory(self, key: str, docs: List[RawDocument], expires_at: float):
        if len(self._memory_cache) >= self.memory_capacity:
            self._memory_cache.popitem(last=False)
        self._memory_cache[key] = (docs, expires_at)

    def get_telemetry(self) -> CostGuardTelemetry:
        """Compute live Cost-Guard metrics."""
        hit_rate = round((self.cache_hits / self.total_searches * 100.0), 1) if self.total_searches > 0 else 0.0
        cost_saved = round(self.cache_hits * self.cost_per_query, 2)
        avg_lat = (
            round(sum(self.latency_samples_ms) / len(self.latency_samples_ms), 1)
            if self.latency_samples_ms
            else 0.0
        )

        return CostGuardTelemetry(
            total_searches=self.total_searches,
            cache_hits=self.cache_hits,
            live_api_calls=self.live_api_calls,
            cache_hit_rate_pct=hit_rate,
            estimated_cost_saved_usd=cost_saved,
            avg_latency_ms=avg_lat,
        )

    def clear(self):
        """Flush memory and disk cache."""
        self._memory_cache.clear()
        try:
            with self._connection() as conn:
                conn.execute("DELETE FROM search_cache")
                conn.commit()
        except Exception:
            pass


# Modern descriptive alias
CostGuardCache = SerpApiCache
