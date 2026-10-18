"""SerpApi Adapter: normalizes raw SerpApi JSON into RawDocument entities."""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from argus.models.domain import RawDocument

logger = logging.getLogger(__name__)


class SerpApiAdapter:
    """Adapts raw SerpApi JSON responses into deterministic RawDocument models."""

    @staticmethod
    def parse_relative_date(date_str: Optional[str]) -> Optional[datetime]:
        """Convert human or relative dates from SerpApi into aware datetime."""
        if not date_str:
            return None

        date_str = date_str.strip()
        now = datetime.now(timezone.utc)

        # Check for relative formats like "3 hours ago", "2 days ago", "5 months ago", "1 year ago"
        rel_match = re.search(r"(\d+)\s+(hour|day|week|month|year)s?\s+ago", date_str, re.IGNORECASE)
        if rel_match:
            val = int(rel_match.group(1))
            unit = rel_match.group(2).lower()
            if unit == "hour":
                return now - relativedelta(hours=val)
            elif unit == "day":
                return now - relativedelta(days=val)
            elif unit == "week":
                return now - relativedelta(weeks=val)
            elif unit == "month":
                return now - relativedelta(months=val)
            elif unit == "year":
                return now - relativedelta(years=val)

        # Check for year only, e.g., "2026" or "2024"
        year_match = re.match(r"^(\d{4})$", date_str)
        if year_match:
            year = int(year_match.group(1))
            return datetime(year, 1, 1, tzinfo=timezone.utc)

        # Common date parsing attempts
        date_formats = [
            "%b %d, %Y",       # Oct 12, 2025
            "%B %d, %Y",       # October 12, 2025
            "%Y-%m-%d",        # 2025-10-12
            "%d %b %Y",        # 12 Oct 2025
            "%m/%d/%Y",        # 10/12/2025
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        # Look for 4-digit year inside string as fallback
        in_str_year = re.search(r"\b(201\d|202\d)\b", date_str)
        if in_str_year:
            year = int(in_str_year.group(1))
            return datetime(year, 6, 1, tzinfo=timezone.utc)

        return None

    @classmethod
    def normalize_serpapi_response(
        cls,
        payload: Dict[str, Any],
        search_vector: Optional[str] = None,
        engine: str = "google",
    ) -> List[RawDocument]:
        """Normalize raw SerpApi JSON (Google, News, etc.) into unique RawDocument items."""
        documents: List[RawDocument] = []
        seen_urls = set()

        # Handle organic_results, news_results, github repositories, and scholar_results
        organic = payload.get("organic_results", [])
        news = payload.get("news_results", [])
        repos = payload.get("repositories", [])
        scholar = payload.get("scholar_results", [])
        combined = organic + news + repos + scholar

        for idx, item in enumerate(combined):
            url = item.get("link") or item.get("url")
            if not url or url in seen_urls:
                continue

            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            snippet = item.get("snippet") or item.get("description") or item.get("summary") or ""
            title = item.get("title") or item.get("name") or ""
            if not snippet and not title:
                continue

            pub_time_raw = item.get("date") or item.get("published_date") or item.get("publication_time")
            pub_date = cls.parse_relative_date(pub_time_raw)

            # Deterministic doc_id
            doc_hash = hashlib.sha256(f"{url}:{title}".encode("utf-8")).hexdigest()[:12]
            doc_id = f"doc_{doc_hash}"

            doc = RawDocument(
                doc_id=doc_id,
                title=title,
                snippet=snippet,
                url=url,
                source_domain=domain,
                publication_time=pub_time_raw,
                published_date=pub_date,
                search_vector=search_vector,
                engine=engine,
                raw_payload={"position": idx, "source": item.get("source")},
            )
            documents.append(doc)
            seen_urls.add(url)

        return documents
