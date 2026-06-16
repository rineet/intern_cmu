from __future__ import annotations

import asyncio
import calendar
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html import unescape
from typing import Iterable

import feedparser
import requests

from ..core.config import Settings
from ..schemas import PaperSummary


OPENALEX_BASE = "https://api.openalex.org/works"
ARXIV_BASE = "https://export.arxiv.org/api/query"


@dataclass(slots=True)
class PaperSourceService:
    settings: Settings

    async def search_openalex(self, query: str, limit: int, timeline_months: int | None = None) -> list[PaperSummary]:
        return await asyncio.to_thread(self._search_openalex_sync, query, limit, timeline_months)

    async def search_arxiv(self, query: str, limit: int, timeline_months: int | None = None) -> list[PaperSummary]:
        return await asyncio.to_thread(self._search_arxiv_sync, query, limit, timeline_months)

    def _search_openalex_sync(self, query: str, limit: int, timeline_months: int | None = None) -> list[PaperSummary]:
        cutoff_date = self._cutoff_date(timeline_months)
        candidate_limit = self._candidate_limit(limit, timeline_months)
        response = requests.get(
            OPENALEX_BASE,
            params={"search": query, "per-page": candidate_limit},
            timeout=self.settings.search_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        papers: list[PaperSummary] = []

        for item in data.get("results", [])[:candidate_limit]:
            authors = [
                author.get("author", {}).get("display_name", "")
                for author in item.get("authorships", [])
                if author.get("author", {}).get("display_name")
            ]
            primary_location = item.get("primary_location") or {}
            source = primary_location.get("source") or {}
            published_at = self._parse_datetime(item.get("publication_date"))
            if cutoff_date and (published_at is None or published_at.date() < cutoff_date):
                continue
            year = published_at.year if published_at else (item.get("publication_year") or item.get("biblio", {}).get("year") or 0)
            doi = self._clean_doi(item.get("doi") or "")
            papers.append(
                PaperSummary(
                    id=self._build_paper_id("openalex", doi, item.get("id") or item.get("display_name") or item.get("title") or ""),
                    title=item.get("title") or "Untitled",
                    abstract=self._reconstruct_openalex_abstract(item.get("abstract_inverted_index")),
                    authors=authors,
                    venue=source.get("display_name") or "OpenAlex",
                    year=int(year or 0),
                    source="openalex",
                    pdf_url=primary_location.get("pdf_url") or primary_location.get("landing_page_url") or item.get("id") or "",
                    doi=doi,
                    published_at=published_at,
                )
            )
        if cutoff_date:
            papers = self._sort_by_published_at(papers)
        return papers[:limit]

    def _search_arxiv_sync(self, query: str, limit: int, timeline_months: int | None = None) -> list[PaperSummary]:
        cutoff_date = self._cutoff_date(timeline_months)
        candidate_limit = self._candidate_limit(limit, timeline_months)
        params = {
            "search_query": self._build_arxiv_query(query, cutoff_date),
            "start": 0,
            "max_results": candidate_limit,
        }
        if cutoff_date:
            params["sortBy"] = "submittedDate"
            params["sortOrder"] = "descending"
        response = requests.get(
            ARXIV_BASE,
            params=params,
            timeout=self.settings.search_timeout_seconds,
        )
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        papers: list[PaperSummary] = []

        for entry in feed.entries[:candidate_limit]:
            title = unescape(entry.get("title", "")).strip() or "Untitled"
            abstract = unescape(entry.get("summary", "")).strip()
            authors = [author.get("name", "") for author in entry.get("authors", []) if author.get("name")]
            published = entry.get("published", "")
            published_at = self._parse_datetime(published)
            if cutoff_date and (published_at is None or published_at.date() < cutoff_date):
                continue
            year = published_at.year if published_at else (int(published[:4]) if published[:4].isdigit() else 0)
            pdf_url = self._extract_arxiv_pdf_link(entry.get("links", []))
            doi = self._clean_doi(entry.get("arxiv_doi") or entry.get("doi") or "")
            papers.append(
                PaperSummary(
                    id=self._build_paper_id("arxiv", doi, entry.get("id") or title),
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    venue="arXiv",
                    year=year,
                    source="arxiv",
                    pdf_url=pdf_url,
                    doi=doi,
                    published_at=published_at,
                )
            )
        if cutoff_date:
            papers = self._sort_by_published_at(papers)
        return papers[:limit]

    @staticmethod
    def _candidate_limit(limit: int, timeline_months: int | None) -> int:
        if not timeline_months:
            return limit
        return min(max(limit * 6, limit), 50)

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
    def _build_arxiv_query(query: str, cutoff_date: date | None) -> str:
        base_query = f"all:{query}"
        if cutoff_date is None:
            return base_query
        start = datetime.combine(cutoff_date, datetime.min.time(), tzinfo=timezone.utc).strftime("%Y%m%d%H%M")
        end = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        return f"{base_query} AND submittedDate:[{start} TO {end}]"

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
    def _extract_arxiv_pdf_link(links: Iterable[dict]) -> str:
        for link in links:
            if link.get("type") == "application/pdf":
                return link.get("href", "")
            if link.get("title", "").lower() == "pdf":
                return link.get("href", "")
        for link in links:
            if link.get("rel") == "alternate":
                return link.get("href", "")
        return ""

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
