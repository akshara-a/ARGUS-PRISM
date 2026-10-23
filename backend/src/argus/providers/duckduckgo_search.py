"""Live Free Web Search Provider backed by DuckDuckGo (Zero API Key Required)."""

import hashlib
import logging
import os
import time
import urllib.parse
from typing import List, Optional
import requests
from dotenv import load_dotenv
from lxml import html

from argus.models.domain import CostGuardTelemetry, RawDocument
from argus.providers.base import ISearchProvider
from argus.providers.cache import SerpApiCache
from argus.providers.mock_provider import MockSearchStrategy

load_dotenv()
logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class DuckDuckGoSearchStrategy(ISearchProvider):
    """Executes live web searches via DuckDuckGo strictly from configured environment endpoints."""

    def __init__(
        self,
        fallback_to_mock: Optional[bool] = None,
        timeout: int = 10,
        cache: Optional[SerpApiCache] = None,
        endpoint: Optional[str] = None,
    ):
        if fallback_to_mock is None:
            mock_env = os.getenv("ARGUS_MOCK_FALLBACK", "false").lower()
            fallback_to_mock = mock_env in ("true", "1", "yes")

        self.fallback_to_mock = fallback_to_mock
        self.timeout = timeout
        self.endpoint = (endpoint or os.getenv("DUCKDUCKGO_ENDPOINT", "")).strip()
        self.mock_provider = MockSearchStrategy() if self.fallback_to_mock else None
        self.cache = cache or SerpApiCache()

    @property
    def provider_name(self) -> str:
        return "DuckDuckGoSearchStrategy (Free Web Search)"

    def get_cost_guard_telemetry(self) -> Optional[CostGuardTelemetry]:
        return self.cache.get_telemetry()

    def search(
        self,
        query: str,
        engine: str = "duckduckgo",
        num_results: int = 5,
        vector_type: Optional[str] = None,
    ) -> List[RawDocument]:
        """Execute search on DuckDuckGo with Cost-Guard caching and RawDocument normalization."""
        # 1. Tiered Cache Lookup
        cached_docs = self.cache.get(
            query=query, engine=engine, num=num_results, vector_type=vector_type
        )
        if cached_docs is not None:
            logger.info("Cost-Guard Cache HIT for query '%s' [%s]", query, engine)
            return cached_docs

        start_time = time.perf_counter()

        # 2. Live Multi-Tier Retrieval (DDGS -> DDG Lite HTML -> Wikipedia Central Index)
        docs: List[RawDocument] = []
        try:
            # Tier A: Modern DDGS Client (Handles TLS browser impersonation)
            docs = self._fetch_ddgs(query, num_results=num_results, vector_type=vector_type)

            # Tier B: HTML Endpoint fallback if DDGS returned 0
            if not docs and self.endpoint and self.endpoint.startswith("http"):
                docs = self._fetch_ddg_html(query, num_results=num_results, vector_type=vector_type)

            # Tier C: Central Open Encyclopedia Index (Zero-key fallback for entities/libraries)
            if not docs:
                docs = self._fetch_wikipedia(query, num_results=num_results, vector_type=vector_type)

            if not docs:
                logger.info("Live search returned 0 results for '%s'", query)
                if self.fallback_to_mock and self.mock_provider:
                    logger.info("Falling back to deterministic mock provider")
                    return self.mock_provider.search(
                        query=query, engine=engine, num_results=num_results, vector_type=vector_type
                    )
        except Exception as exc:
            logger.warning("Live retrieval failed: %s", exc)
            if self.fallback_to_mock and self.mock_provider:
                logger.info("Falling back to deterministic mock provider")
                return self.mock_provider.search(
                    query=query, engine=engine, num_results=num_results, vector_type=vector_type
                )
            docs = []

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # 3. Store in Tier 1 & Tier 2 Cost-Guard Cache (Only cache non-empty result sets)
        if docs:
            self.cache.put(
                query=query,
                documents=docs,
                engine=engine,
                num=num_results,
                fetch_latency_ms=latency_ms,
                vector_type=vector_type,
            )

        return docs

    def _fetch_ddgs(
        self,
        query: str,
        num_results: int = 5,
        vector_type: Optional[str] = None,
    ) -> List[RawDocument]:
        """Query DuckDuckGo using modern DDGS client with TLS fingerprint spoofing."""
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            documents: List[RawDocument] = []
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))
                for item in results:
                    title = (item.get("title") or "").strip()
                    target_url = (item.get("href") or "").strip()
                    snippet = (item.get("body") or "").strip() or title

                    if not title or not target_url or not target_url.startswith("http"):
                        continue

                    parsed_url = urllib.parse.urlparse(target_url)
                    domain = parsed_url.netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]

                    doc_id = f"doc_ddg_{hashlib.md5(target_url.encode()).hexdigest()[:8]}"
                    documents.append(
                        RawDocument(
                            doc_id=doc_id,
                            title=title,
                            snippet=snippet,
                            url=target_url,
                            source_domain=domain,
                            publication_time=None,
                            search_vector=vector_type,
                            engine="duckduckgo",
                        )
                    )
            return documents
        except Exception as exc:
            logger.debug("DDGS client query encountered note: %s", exc)
            return []

    def _fetch_wikipedia(
        self,
        query: str,
        num_results: int = 3,
        vector_type: Optional[str] = None,
    ) -> List[RawDocument]:
        """Query Wikipedia Central Index REST API for technical entities and definitions."""
        try:
            stop_terms = {
                "architecture", "documentation", "issues", "bottleneck", "changelog",
                "release", "notes", "official", "production", "ready", "features", "breaking"
            }
            terms = [w for w in query.split() if w.lower() not in stop_terms and len(w) > 2]
            search_term = " ".join(terms[:3]) if terms else query

            headers = {"User-Agent": "ArgusPrism/1.0 (academic research)"}
            resp = requests.get(
                "https://en.wikipedia.org/w/rest.php/v1/search/page",
                params={"q": search_term, "limit": num_results},
                headers=headers,
                timeout=min(5, self.timeout),
            )
            if resp.status_code != 200:
                return []

            documents: List[RawDocument] = []
            data = resp.json()
            for page in data.get("pages", []):
                title = (page.get("title") or "").strip()
                desc = (page.get("description") or "").strip()
                key = (page.get("key") or "").strip()
                target_url = f"https://en.wikipedia.org/wiki/{key}" if key else ""
                snippet = f"{title}: {desc}" if desc else title

                if not title or not target_url:
                    continue

                doc_id = f"doc_wiki_{hashlib.md5(target_url.encode()).hexdigest()[:8]}"
                documents.append(
                    RawDocument(
                        doc_id=doc_id,
                        title=title,
                        snippet=snippet,
                        url=target_url,
                        source_domain="wikipedia.org",
                        publication_time=None,
                        search_vector=vector_type,
                        engine="duckduckgo",
                    )
                )
            return documents
        except Exception as exc:
            logger.debug("Wikipedia central index fallback note: %s", exc)
            return []

    def _fetch_ddg_html(
        self,
        query: str,
        num_results: int = 5,
        vector_type: Optional[str] = None,
    ) -> List[RawDocument]:
        """Query DuckDuckGo Lite endpoint and parse into RawDocument entities."""
        if not self.endpoint or not self.endpoint.startswith("http"):
            logger.debug("DuckDuckGo HTML retrieval skipped: DUCKDUCKGO_ENDPOINT is not configured.")
            return []

        headers = {
            "User-Agent": USER_AGENT,
            "Referer": os.getenv("DUCKDUCKGO_REFERER", self.endpoint),
        }
        data = {"q": query}

        resp = requests.post(
            self.endpoint,
            data=data,
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        tree = html.fromstring(resp.content)
        documents: List[RawDocument] = []

        link_elems = tree.xpath('//a[@class="result-link"]')
        snippet_tds = tree.xpath('//td[@class="result-snippet"]')

        for i, a_elem in enumerate(link_elems[:num_results]):
            title = a_elem.text_content().strip()
            raw_href = a_elem.get("href", "")

            # Unpack DuckDuckGo redirect link if present
            if "uddg=" in raw_href:
                parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                target_url = parsed_query.get("uddg", [raw_href])[0]
            else:
                target_url = raw_href

            snippet = snippet_tds[i].text_content().strip() if i < len(snippet_tds) else title
            if not title or not target_url or not target_url.startswith("http"):
                continue

            # Extract source domain
            parsed_url = urllib.parse.urlparse(target_url)
            domain = parsed_url.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            doc_id = f"doc_ddg_{hashlib.md5(target_url.encode()).hexdigest()[:8]}"
            documents.append(
                RawDocument(
                    doc_id=doc_id,
                    title=title,
                    snippet=snippet or title,
                    url=target_url,
                    source_domain=domain,
                    publication_time=None,
                    search_vector=vector_type,
                    engine="duckduckgo",
                )
            )

        return documents
