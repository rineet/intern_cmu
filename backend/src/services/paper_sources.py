from __future__ import annotations

import asyncio
import calendar
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import requests

from ..core.config import Settings
from ..schemas import PaperSummary

OPENALEX_BASE = "https://api.openalex.org/works"


@dataclass(slots=True)
class PaperSourceService:
    settings: Settings

    _openalex_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _last_openalex_request: float = 0.0

    async def search_openalex_keyword(
        self,
        query: str,
        limit: int,
        timeline_months: int | None = None,
    ) -> list[PaperSummary]:
        """Search OpenAlex using standard keyword lexical search."""
        await self._wait_for_openalex()
        return await asyncio.to_thread(
            self._search_openalex_sync,
            query,
            limit,
            timeline_months,
            False,
        )

    async def search_openalex_semantic(
        self,
        query: str,
        limit: int,
        timeline_months: int | None = None,
    ) -> list[PaperSummary]:
        """Search OpenAlex using natural language semantic search."""
        await self._wait_for_openalex()
        return await asyncio.to_thread(
            self._search_openalex_sync,
            query,
            limit,
            timeline_months,
            True,
        )

    async def search_openalex(
        self,
        query: str,
        limit: int,
        timeline_months: int | None = None,
    ) -> list[PaperSummary]:
        """Default search alias (defaults to lexical search)."""
        return await self.search_openalex_keyword(query, limit, timeline_months)

    async def _wait_for_openalex(self) -> None:
        """Enforces rate limiting (1 second minimum between requests)."""
        async with self._openalex_lock:
            now = time.monotonic()
            elapsed = now - self._last_openalex_request

            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

            self._last_openalex_request = time.monotonic()

    def _search_openalex_sync(
        self,
        query: str,
        limit: int,
        timeline_months: int | None = None,
        semantic: bool = False,
    ) -> list[PaperSummary]:
        cutoff_date = self._cutoff_date(timeline_months)
        candidate_limit = self._candidate_limit(limit, timeline_months)

        headers = {
            "User-Agent": f"ResearchFinder/1.0 ({self.settings.MAIL})"
        }

        params: dict[str, Any] = {
            "api_key": getattr(self.settings, "OpenAlex_api_key", None),
            "mailto": self.settings.MAIL,
        }

        if semantic:
            params["search.semantic"] = query
            params["per-page"] = min(candidate_limit, 50)  # Max semantic limit is 50
        else:
            params["search"] = query
            params["per-page"] = min(candidate_limit, 200)

        response = None
        for attempt in range(5):
            response = requests.get(
                OPENALEX_BASE,
                params=params,
                headers=headers,
                timeout=self.settings.search_timeout_seconds,
            )

            if response.status_code in {429, 500, 502, 503, 504}:
                wait = 2**attempt
                print(
                    f"OpenAlex returned {response.status_code}. "
                    f"Retry {attempt + 1}/5 after {wait} seconds."
                )
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print("Status:", response.status_code)
                print("Response:", response.text)

            response.raise_for_status()
            break

        if not response:
            return []

        data = response.json()
        results = data.get("results", [])

        print("Status Code:", response.status_code)
        print("Total OpenAlex Results:", data.get("meta", {}).get("count"))
        print("Returned Results:", len(results))

        papers: list[PaperSummary] = []

        for item in results[:candidate_limit]:
            published_at = self._parse_datetime(item.get("publication_date"))
            if cutoff_date and (published_at is None or published_at.date() < cutoff_date):
                continue

            # Extract Primary Location & Source Metadata
            primary_loc = item.get("primary_location") or {}
            source_info = primary_loc.get("source") or {}

            # Venue / Journal Name & Publisher
            venue = source_info.get("display_name") or "OpenAlex"
            publisher = source_info.get("host_organization_name") or ""

            # Extract Authors & Institutional Affiliations
            authors: list[str] = []
            affiliations: list[str] = []
            for authorship in item.get("authorships", []):
                author_name = authorship.get("author", {}).get("display_name")
                if author_name:
                    authors.append(author_name)
                for inst in authorship.get("institutions", []):
                    inst_name = inst.get("display_name")
                    if inst_name and inst_name not in affiliations:
                        affiliations.append(inst_name)

            # Dates and Identifier Metadata
            year = (
                published_at.year
                if published_at
                else (item.get("publication_year") or item.get("biblio", {}).get("year") or 0)
            )
            doi = self._clean_doi(item.get("doi") or "")

            # Open Access & Links
            oa_info = item.get("open_access") or {}
            is_oa = oa_info.get("is_oa", False)
            oa_status = oa_info.get("oa_status", "closed")
            pdf_url = (
                primary_loc.get("pdf_url")
                or oa_info.get("oa_url")
                or primary_loc.get("landing_page_url")
                or item.get("id")
                or ""
            )

            # OpenAlex Metrics & Concepts
            citation_count = item.get("cited_by_count", 0)
            topics = [
                t.get("display_name")
                for t in item.get("topics", [])
                if t.get("display_name")
            ]
            concepts = [
                c.get("display_name")
                for c in item.get("concepts", [])
                if c.get("display_name")
            ]

            # Bibliographic info
            biblio = item.get("biblio") or {}

            papers.append(
                PaperSummary(
                    id=self._build_paper_id(
                        "openalex",
                        doi,
                        item.get("id") or item.get("display_name") or item.get("title") or "",
                    ),
                    title=item.get("title") or "Untitled",
                    abstract=self._reconstruct_openalex_abstract(item.get("abstract_inverted_index")),
                    authors=authors,
                    venue=venue,
                    year=int(year or 0),
                    source="openalex",
                    pdf_url=pdf_url,
                    doi=doi,
                    published_at=published_at,
                    citation_count=citation_count,
                    # Optional extended metadata fields (pass if defined in your schema/dataclass)
                    # publisher=publisher,
                    # is_oa=is_oa,
                    # oa_status=oa_status,
                    # license=primary_loc.get("license"),
                    # topics=topics,
                    # concepts=concepts,
                    # affiliations=affiliations,
                    # volume=biblio.get("volume"),
                    # issue=biblio.get("issue"),
                    # first_page=biblio.get("first_page"),
                    # last_page=biblio.get("last_page"),
                    # is_retracted=item.get("is_retracted", False),
                )
            )

        print(f"Created {len(papers)} PaperSummary objects")
        if cutoff_date:
            papers = self._sort_by_published_at(papers)

        return papers[:limit]

    @staticmethod
    def _candidate_limit(limit: int, timeline_months: int | None) -> int:
        if not timeline_months:
            return limit
        return min(max(limit * 6, limit), 200)

    @staticmethod
    def _cutoff_date(timeline_months: int | None) -> date | None:
        if not timeline_months:
            return None
        today = datetime.now(timezone.utc).date()
        month = today.month - timeline_months
        year = today.year
        while month <= 0:
            year -= 1
            month += 12
        day = min(today.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            return None

    @staticmethod
    def _sort_by_published_at(papers: list[PaperSummary]) -> list[PaperSummary]:
        return sorted(
            papers,
            key=lambda paper: paper.published_at or datetime.min,
            reverse=True,
        )

    @staticmethod
    def _reconstruct_openalex_abstract(index: object) -> str:
        if not isinstance(index, dict):
            return ""
        positions: list[tuple[int, str]] = []
        for word, indexes in index.items():
            if not isinstance(indexes, list):
                continue
            for position in indexes:
                positions.append((int(position), word))
        positions.sort(key=lambda item: item[0])
        return " ".join(word for _, word in positions)

    @staticmethod
    def _build_paper_id(source: str, doi: str, fallback: str) -> str:
        identifier = doi or fallback
        slug = identifier.lower().replace("https://doi.org/", "")
        slug = slug.replace("/", "-").replace(" ", "-")
        return f"{source}:{slug[:180]}"

    @staticmethod
    def _clean_doi(doi: str) -> str:
        return doi.replace("https://doi.org/", "").strip()