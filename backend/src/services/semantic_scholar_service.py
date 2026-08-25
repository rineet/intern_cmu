from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests
from requests import Response

from ..core.config import Settings
from ..schemas import PaperSummary

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"

# --- GLOBAL RATE LIMITING STATE ---
_global_last_request_time: float = 0.0
_global_rate_limit_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _global_rate_limit_lock
    if _global_rate_limit_lock is None:
        _global_rate_limit_lock = asyncio.Lock()
    return _global_rate_limit_lock


@dataclass(slots=True)
class SemanticScholarService:
    settings: Settings
    _session: requests.Session = field(default_factory=requests.Session)

    def __post_init__(self) -> None:
        """Sanitize the API key and configure default session headers."""
        raw_key = getattr(self.settings, "semantic_scholar_api_key", None)
        if raw_key and raw_key.strip():
            clean_key = raw_key.strip().strip("'\"")
            self._session.headers.update(
                {
                    "User-Agent": "ResearchFinder/1.0",
                    "x-api-key": clean_key,
                }
            )
            logger.info(
                "[SemanticScholarService] Initialized WITH API Key: %s...",
                clean_key[:4],
            )
        else:
            self._session.headers.update({"User-Agent": "ResearchFinder/1.0"})
            logger.warning(
                "[SemanticScholarService] Initialized WITHOUT API Key! "
                "Requests will fall back to strict public rate limits."
            )

    @property
    def min_request_interval(self) -> float:
        """
        Pacing interval between requests:
        - Authenticated: 3.0 seconds (prevents burst 429s on heavy endpoints)
        - Public/Unauthenticated: 3.5 seconds
        """
        has_key = "x-api-key" in self._session.headers
        return 3.0 if has_key else 3.5

    async def _wait_for_rate_limit(self) -> None:
        global _global_last_request_time
        lock = _get_lock()
        interval = self.min_request_interval

        async with lock:
            now = time.monotonic()
            elapsed = now - _global_last_request_time

            if elapsed < interval:
                sleep_time = interval - elapsed
                logger.info(
                    "Pacing API requests: Sleeping %.2fs...", sleep_time
                )
                await asyncio.sleep(sleep_time)

            _global_last_request_time = time.monotonic()

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Response | None:
        max_attempts = 4
        has_key = "x-api-key" in self._session.headers

        for attempt in range(max_attempts):
            await self._wait_for_rate_limit()

            try:
                logger.info(
                    "Semantic Scholar Request [%s]: %s %s params=%s",
                    "AUTHENTICATED" if has_key else "PUBLIC",
                    method,
                    url,
                    kwargs.get("params"),
                )

                response = await asyncio.to_thread(
                    self._session.request,
                    method,
                    url,
                    **kwargs,
                )

                # --- RATE LIMIT FIX ---
                lock = _get_lock()
                async with lock:
                    global _global_last_request_time
                    _global_last_request_time = time.monotonic()
                # ----------------------

                logger.info(
                    "Semantic Scholar Response: %d",
                    response.status_code,
                )

            except requests.exceptions.RequestException as e:
                logger.exception(
                    "Semantic Scholar request failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_attempts,
                    e,
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                return None

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = (
                    float(retry_after)
                    if retry_after
                    else (15.0 * (attempt + 1))
                )

                logger.warning(
                    "Semantic Scholar rate limited (429). "
                    "Attempt %d/%d. Waiting %.1fs before retrying.",
                    attempt + 1,
                    max_attempts,
                    wait_time,
                )

                await asyncio.sleep(wait_time)
                continue

            if response.status_code in (500, 502, 503, 504):
                logger.warning(
                    "Semantic Scholar server error %d. Attempt %d/%d",
                    response.status_code,
                    attempt + 1,
                    max_attempts,
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                return None

            if (
                response.status_code >= 400
                and response.status_code != 404
                and response.status_code != 429
            ):
                logger.error(
                    "HTTP %d\nURL=%s\nParams=%s\nBody=%s",
                    response.status_code,
                    url,
                    kwargs.get("params"),
                    response.text[:500],
                )

            if response.status_code == 404:
                return None

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                logger.exception("HTTP error %d", response.status_code)
                return None

            return response

        logger.error(
            "Semantic Scholar request exhausted all retries. URL=%s Params=%s",
            url,
            kwargs.get("params"),
        )
        return None

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Parses Semantic Scholar's YYYY-MM-DD into a datetime object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    def _extract_paper_summary(self, item: dict) -> PaperSummary:
        """Helper to standardize parsing across search and graph expansion."""
        external = item.get("externalIds") or {}
        oa_pdf = item.get("openAccessPdf") or {}
        journal = item.get("journal") or {}
        
        # PDF URL Logic: Try the direct PDF link first, fallback to standard URL
        pdf_url = oa_pdf.get("url") or item.get("url") or ""
        
        # Date parsing
        published_at = self._parse_date(item.get("publicationDate"))

        # Venue logic: Journal name is often cleaner than raw venue
        venue = journal.get("name") or item.get("venue") or "Semantic Scholar"

        # Topics extraction
        topics = [
            f.get("category")
            for f in item.get("s2FieldsOfStudy", [])
            if isinstance(f, dict) and f.get("category")
        ]

        return PaperSummary(
            id=f"semantic:{item.get('paperId', '')}",
            title=item.get("title") or "Untitled",
            abstract=item.get("abstract") or "",
            authors=[
                a.get("name")
                for a in item.get("authors", [])
                if isinstance(a, dict) and a.get("name")
            ],
            venue=venue,
            year=item.get("year") or 0,
            source="semantic_scholar",
            pdf_url=pdf_url,
            doi=external.get("DOI") or "",
            published_at=published_at,
            citation_count=item.get("citationCount", 0),
            
            # Additional Optional Fields matching OpenAlex (Uncomment if in your schema)
            # is_oa=item.get("isOpenAccess", False),
            # topics=topics,
            # volume=journal.get("volume"),
            # pages=journal.get("pages"),
        )

    async def expand_from_paper(
        self,
        paper: PaperSummary,
    ) -> list[PaperSummary]:
        if not paper.title and not paper.id:
            return []

        # --- OPTIMIZATION: DIRECT ID RESOLUTION ---
        target_paper_id = None

        if paper.id and paper.id.startswith("semantic:"):
            target_paper_id = paper.id.replace("semantic:", "").strip()
        elif paper.doi:
            clean_doi = paper.doi.strip()
            if "arxiv" in clean_doi.lower():
                arxiv_id = clean_doi.lower().split("arxiv.")[-1]
                target_paper_id = f"ARXIV:{arxiv_id}"
            else:
                target_paper_id = f"DOI:{clean_doi}"

        if not target_paper_id and paper.title:
            response = await self._request(
                "GET",
                f"{SEMANTIC_SCHOLAR_BASE}/paper/search",
                params={
                    "query": paper.title,
                    "limit": 1,
                    "fields": "paperId,title",
                },
                timeout=30,
            )

            if response is None:
                logger.warning(
                    "Title search resolution failed for '%s'. Skipping expansion.",
                    paper.title,
                )
                return []

            data = response.json()
            if data.get("data"):
                target_paper_id = data["data"][0]["paperId"]

        if not target_paper_id:
            logger.warning(
                "Could not resolve Semantic Scholar ID for paper: '%s'",
                paper.title,
            )
            return []

        # Request extended fields for citations and references
        fields_to_request = (
            "title,year,venue,"
            "references.paperId,references.title,references.abstract,"
            "references.year,references.authors,references.externalIds,"
            "references.venue,references.publicationDate,references.citationCount,"
            "references.openAccessPdf,references.journal,references.s2FieldsOfStudy,"
            "citations.paperId,citations.title,citations.abstract,"
            "citations.year,citations.authors,citations.externalIds,"
            "citations.venue,citations.publicationDate,citations.citationCount,"
            "citations.openAccessPdf,citations.journal,citations.s2FieldsOfStudy"
        )

        response = await self._request(
            "GET",
            f"{SEMANTIC_SCHOLAR_BASE}/paper/{target_paper_id}",
            params={"fields": fields_to_request},
            timeout=30,
        )

        if response is None:
            logger.warning(
                "Failed to fetch citations/references for paper ID '%s'.",
                target_paper_id,
            )
            return []

        data = response.json()

        papers: list[PaperSummary] = []
        seen: set[str] = set()

        references = data.get("references") or []
        citations = data.get("citations") or []

        for collection in (references, citations):
            for item in collection:
                p_id = item.get("paperId")
                if not p_id or p_id in seen:
                    continue

                seen.add(p_id)
                papers.append(self._extract_paper_summary(item))

        return papers

    async def _search(
        self,
        query: str,
        limit: int,
    ) -> list[PaperSummary]:
        response = await self._request(
            "GET",
            f"{SEMANTIC_SCHOLAR_BASE}/paper/search",
            params={
                "query": query,
                "limit": limit,
                "fields": (
                    "paperId,title,abstract,year,venue,"
                    "authors,externalIds,url,openAccessPdf,"
                    "publicationDate,citationCount,journal,s2FieldsOfStudy,isOpenAccess"
                ),
            },
            timeout=30,
        )

        if response is None:
            logger.error("Search failed for query='%s'", query)
            return []

        data = response.json()
        papers = []

        for item in data.get("data", []):
            papers.append(self._extract_paper_summary(item))

        return papers

    async def search(
        self,
        query: str,
        limit: int,
    ) -> list[PaperSummary]:
        return await self._search(query, limit)