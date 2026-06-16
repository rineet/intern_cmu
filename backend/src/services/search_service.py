from __future__ import annotations

import asyncio
import logging

from ..core.config import Settings
from ..repositories.search_repository import SearchRepository
from ..schemas import ExpandedKeywords, PaperSummary, SearchResponse
from .deduplication import deduplicate_papers
from .gemini_service import GeminiKeywordService
from .paper_sources import PaperSourceService


logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        settings: Settings,
        repository: SearchRepository,
        keyword_service: GeminiKeywordService,
        source_service: PaperSourceService,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.keyword_service = keyword_service
        self.source_service = source_service

    async def search(self, query: str, timeline_months: int | None = None) -> SearchResponse:
        expanded_keywords = await asyncio.to_thread(
            self.keyword_service.expand,
            query,
        )
        search_terms = self._build_search_terms(query, expanded_keywords, self.settings.max_expanded_terms)
        # logger.info(
        #     "Final search terms: %s",
        #     search_terms,
        # )
        async def safe_search_openalex(term: str) -> list[PaperSummary]:
            try:
                return await self.source_service.search_openalex(term, self.settings.search_limit_per_source, timeline_months)
            except Exception as e:
                logger.exception(f"OpenAlex search failed for term '{term}': {e}")
                return []

        async def safe_search_arxiv(term: str) -> list[PaperSummary]:
            try:
                return await self.source_service.search_arxiv(term, self.settings.search_limit_per_source, timeline_months)
            except Exception as e:
                logger.exception(f"ArXiv search failed for term '{term}': {e}")
                return []

        tasks = []
        # Query OpenAlex for all terms
        for term in search_terms:
            tasks.append(safe_search_openalex(term))
        
        # Query ArXiv ONLY for the primary/original query (which is search_terms[0]) to avoid 429 rate limit issues
        if search_terms:
            tasks.append(safe_search_arxiv(search_terms[0]))

        results = await asyncio.gather(
            *tasks,
            return_exceptions=False,
        )
        papers: list[PaperSummary] = []
        for result in results:
            papers.extend(result)

        deduped_papers = deduplicate_papers(papers)
        search_record = await asyncio.to_thread(
            self.repository.create_search,
            query,
            expanded_keywords,
        )

        await asyncio.to_thread(
            self.repository.save_papers,
            search_record.id,
            deduped_papers,
        )
        return SearchResponse(
            search_id=search_record.id,
            query=query,
            timeline_months=timeline_months,
            expanded_keywords=expanded_keywords,
            papers=deduped_papers,
            created_at=search_record.created_at,
        )

    @staticmethod
    def _build_search_terms(query: str, keywords: ExpandedKeywords, max_expanded_terms: int) -> list[str]:
        ordered: list[str] = []
        # Prioritize original query first
        ordered.append(query.strip())
        ordered.extend(keywords.canonical_terms)
        ordered.extend(keywords.related_terms)
        ordered.extend(keywords.search_queries)
        ordered.extend(keywords.expanded_terms)
        # ordered.extend(keywords.acronyms)
        # ordered.extend(keywords.research_domains)

        deduped: list[str] = []
        seen: set[str] = set()
        for term in ordered:
            cleaned = " ".join(term.strip().lower().split())
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            deduped.append(cleaned)
        
        # Limit to max_expanded_terms search terms to prevent aggressive rate limiting
        return deduped[:min(6,max_expanded_terms)]
