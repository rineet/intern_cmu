from __future__ import annotations
import os
import re
import json
import asyncio
import logging
from datetime import datetime

from fastapi import HTTPException

from ..core.config import Settings
from ..repositories.search_repository import SearchRepository
from ..schemas import ExpandedKeywords, SearchResponse
from .deduplication import deduplicate_papers
from .gemini_service import GeminiKeywordService, GeminiBusyException
from .gemini_seed_selection import GeminiSeedSelector
from .paper_sources import PaperSourceService
from .semantic_scholar_service import SemanticScholarService
from .gemini_config_service import GeminiConfigService

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        settings: Settings,
        repository: SearchRepository,
        keyword_service: GeminiKeywordService,
        source_service: PaperSourceService,
        semantic_service: SemanticScholarService,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.keyword_service = keyword_service
        self.source_service = source_service
        self.semantic_service = semantic_service
        
        try:
            self.config_service = GeminiConfigService()
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini configuration service: {e}")
            self.config_service = None

        try:
            if settings.reranker_mode == "remote":
                from .reranker_service import RerankerService
                self.reranker = RerankerService(settings)
            elif settings.reranker_mode == "local":
                from .reranker_service_offline import RerankerService
                self.reranker = RerankerService(settings)
            elif settings.reranker_mode == "disabled":
                self.reranker = None
            else:
                raise ValueError("RERANKER_MODE must be 'remote', 'local', or 'disabled'.")
        except Exception as e:
            logger.warning(f"Failed to initialize reranker: {e}")
            self.reranker = None

        try:
            self.seed_selector = GeminiSeedSelector()
        except Exception:
            self.seed_selector = None

    @staticmethod
    def papers_to_json(papers):
        return [p.model_dump(mode="json") for p in papers]

    async def search(self, query: str, timeline_months: int | None = None, top_k: int = 50) -> SearchResponse:
        # --- 1. Keyword Expansion with Gemini Busy Early-Exit ---
        try:
            expanded_keywords = await asyncio.to_thread(
                self.keyword_service.expand,
                query,
            )
            
            fallback_config = {
                "DYNAMIC_ASPECTS": [query],
                "CLEAN_INTENT_QUERY": query,
                "PENALTY_TERMS": [],
                "BASELINE_MODELS": []
            }
            dynamic_config = await asyncio.to_thread(
                self.config_service.generate_config,
                query,
            ) if self.config_service else fallback_config
            
        except GeminiBusyException as e:
            logger.error("Search aborted: Gemini API busy during keyword expansion: %s", e)
            raise HTTPException(
                status_code=503,
                detail="Gemini is kinda busy, please try again later."
            )

        search_terms = self._build_search_terms(
            query, expanded_keywords, self.settings.max_expanded_terms
        )
        
        run_folder = os.path.join(
            "search_outputs", datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        os.makedirs(run_folder, exist_ok=True)
        os.makedirs(os.path.join(run_folder, "openalex_keyword"), exist_ok=True)
        os.makedirs(os.path.join(run_folder, "semantic_keyword"), exist_ok=True)
        os.makedirs(os.path.join(run_folder, "citation"), exist_ok=True)

        if self.config_service:
            config_file_path = os.path.join(run_folder, "dynamic_config.json")
            await asyncio.to_thread(
                self.config_service.save_config_to_json,
                dynamic_config, 
                config_file_path
            )
            
        debug_info = {
            "original_query": query,
            "search_terms": search_terms,
            "sources": {
                "openalex_keyword": [],
                "semantic_scholar_keyword": [],
            },
            "citation_expansion": {
                "top10_papers": [],
                "expanded_from": [],
            },
        }

        async def safe_semantic_scholar(term):
            try:
                debug_info["sources"]["semantic_scholar_keyword"].append(term)
                return await self.semantic_service.search(
                    term,
                    self.settings.search_limit_per_source,
                )
            except Exception as e:
                logger.exception(f"Semantic Scholar keyword search failed for '{term}': {e}")
                return []

        async def safe_search_openalex_keyword(term: str):
            try:
                debug_info["sources"]["openalex_keyword"].append(term)
                return await self.source_service.search_openalex_keyword(
                    term,
                    self.settings.search_limit_per_source,
                    timeline_months,
                )
            except Exception as e:
                logger.exception(f"Keyword search failed for '{term}': {e}")
                return []

        papers = []
        source_results = {
            "openalex_keyword": [],
            "semantic_scholar_keyword": [],
            "semantic_scholar_citation": [],
        }

        # --- OpenAlex Keyword Search (Concurrent) ---
        openalex_tasks = [safe_search_openalex_keyword(term) for term in search_terms]
        openalex_results = await asyncio.gather(*openalex_tasks)
        
        for term, results in zip(search_terms, openalex_results):
            source_results["openalex_keyword"].extend(results)
            filename = re.sub(r'[^a-zA-Z0-9_-]', "_", term)[:100]
            with open(os.path.join(run_folder, "openalex_keyword", f"{filename}.json"), "w", encoding="utf-8") as f:
                json.dump({"query": term, "papers": self.papers_to_json(results)}, f, indent=2, ensure_ascii=False)

        with open(os.path.join(run_folder, "openalex_keyword", "all_results.json"), "w", encoding="utf-8") as f:
            json.dump({
                "query": "Merged Results",
                "papers": self.papers_to_json(source_results["openalex_keyword"])
            }, f, indent=2, ensure_ascii=False)

        # --- Semantic Scholar Keyword Search (STRICTLY SEQUENTIAL) ---
        for term in search_terms:
            results = await safe_semantic_scholar(term)
            source_results["semantic_scholar_keyword"].extend(results)
            
            filename = re.sub(r'[^a-zA-Z0-9_-]', "_", term)[:100]
            with open(os.path.join(run_folder, "semantic_keyword", f"{filename}.json"), "w", encoding="utf-8") as f:
                json.dump({"query": term, "papers": self.papers_to_json(results)}, f, indent=2, ensure_ascii=False)

        with open(os.path.join(run_folder, "semantic_keyword", "all_results.json"), "w", encoding="utf-8") as f:
            json.dump({
                "query": "Merged Results",
                "papers": self.papers_to_json(source_results["semantic_scholar_keyword"])
            }, f, indent=2, ensure_ascii=False)

        # --- Deduplication and Raw List ---
        for source in source_results.values():
            papers.extend(source)
            
        deduped_papers = deduplicate_papers(papers)
        ranked = [p for p in deduped_papers if p.title]

        with open(os.path.join(run_folder, "ranked_before_citation_expansion.json"), "w", encoding="utf-8") as f:
            json.dump(self.papers_to_json(ranked), f, indent=2, ensure_ascii=False)

        top_papers = ranked[:10]
        
        # --- Gemini Seed Selection ---
        if self.seed_selector and ranked:
            try:
                selected = await asyncio.to_thread(
                    self.seed_selector.select_seeds,
                    self.papers_to_json(ranked),
                    query,
                    top_n=min(10, len(ranked)),
                )
                
                if isinstance(selected, list):
                    selected_ids = {
                        item.get("id") or item.get("doi") or item.get("title")
                        for item in selected if isinstance(item, dict)
                    }
                    seeded = [
                        paper for paper in ranked
                        if paper.id in selected_ids or paper.doi in selected_ids or paper.title in selected_ids
                    ][:10]
                    
                    if seeded:
                        top_papers = seeded
                        
            except GeminiBusyException as e:
                logger.error("Search aborted: Gemini API busy during seed selection: %s", e)
                raise HTTPException(
                    status_code=503,
                    detail="Gemini is kinda busy, please try again later."
                )
            except Exception as e:
                logger.exception(f"Gemini seed selection failed: {e}")

        debug_info["citation_expansion"]["top10_papers"] = [
            {"title": p.title, "year": p.year, "doi": p.doi, "venue": p.venue}
            for p in top_papers
        ]

        # --- Semantic Scholar Citation Expansion (STRICTLY SEQUENTIAL) ---
        for paper in top_papers:
            debug_info["citation_expansion"]["expanded_from"].append(
                {"title": paper.title, "year": paper.year, "doi": paper.doi}
            )
            try:
                output = await self.semantic_service.expand_from_paper(paper)
                source_results["semantic_scholar_citation"].extend(output)
                
                filename = re.sub(r'[^a-zA-Z0-9_-]', "_", paper.title)[:100]
                with open(os.path.join(run_folder, "citation", f"{filename}.json"), "w", encoding="utf-8") as f:
                    json.dump({"query": paper.title, "papers": self.papers_to_json(output)}, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.exception(f"Citation expansion failed for '{paper.title}': {e}")

        with open(os.path.join(run_folder, "citation", "all_results.json"), "w", encoding="utf-8") as f:
            json.dump({
                "query": "Merged Results",
                "papers": self.papers_to_json(source_results["semantic_scholar_citation"])
            }, f, indent=2, ensure_ascii=False)

        papers = []
        for source in source_results.values():
            papers.extend(source)

        with open(os.path.join(run_folder, "debug_search.json"), "w", encoding="utf-8") as f:
            json.dump(debug_info, f, indent=2, ensure_ascii=False)

        with open(os.path.join(run_folder, "merged_before_dedup.json"), "w", encoding="utf-8") as f:
            json.dump(self.papers_to_json(papers), f, indent=2, ensure_ascii=False)

        final_deduped_papers = await asyncio.to_thread(deduplicate_papers, papers)

        # --- Final reranking: remote Colab GPU or local GPU, selected by RERANKER_MODE ---
        if self.reranker:
            logger.info("Executing GPU Reranking on ALL %d papers...", len(final_deduped_papers))
            # top_k=None ensures we rerank and return ALL ~3,000 papers
            final_deduped_papers = await asyncio.to_thread(
                self.reranker.rerank, 
                final_deduped_papers, 
                dynamic_config,
                None
            )

        with open(os.path.join(run_folder, "merged_after_dedup.json"), "w", encoding="utf-8") as f:
            json.dump(self.papers_to_json(final_deduped_papers), f, indent=2, ensure_ascii=False)

        # Save search record
        search_record = await asyncio.to_thread(
            self.repository.create_search,
            query,
            expanded_keywords,
        )

        # SAVE ALL ~3,000 RERANKED PAPERS IN DUCKDB IN RANKED ORDER
        await asyncio.to_thread(
            self.repository.save_papers,
            search_record.id,
            final_deduped_papers,
        )
        
        print("Saved total papers in DB:", len(final_deduped_papers))
        
        # Slice only top_k (default 50 or user-specified) for the immediate response
        response_papers = final_deduped_papers
        print(f"Returning top {len(response_papers)} papers to caller.")
        
        response = SearchResponse(
            search_id=search_record.id,
            query=query,
            timeline_months=timeline_months,
            expanded_keywords=expanded_keywords,
            papers=response_papers,
            created_at=search_record.created_at,
        )

        with open(os.path.join(run_folder, "final_response.json"), "w", encoding="utf-8") as f:
            json.dump(response.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
            
        return response

    @staticmethod
    def _build_search_terms(query: str, keywords: ExpandedKeywords, max_expanded_terms: int) -> list[str]:
        ordered: list[str] = []
        ordered.extend(keywords.search_queries)

        deduped_dict = {}
        for term in ordered:
            cleaned = " ".join(term.strip().lower().split())
            if cleaned:
                deduped_dict[cleaned] = None
        
        return list(deduped_dict.keys())[:min(15, max_expanded_terms)]
