from __future__ import annotations

import logging
import requests
from ..core.config import Settings
from ..schemas import PaperSummary

logger = logging.getLogger(__name__)


class RerankerService:
    """Delegates heavy model execution to the Google Colab GPU microservice."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.colab_url = settings.colab_reranker_url
        logger.info(f"🔧 RerankerService initialized. Target URL is: {self.colab_url}")

    def rerank(
        self,
        papers: list[PaperSummary],
        dynamic_config: dict,
        top_k: int | None = None,
    ) -> list[PaperSummary]:
        if not papers:
            return []

        paper_map: dict[str, PaperSummary] = {p.id: p for p in papers}
        dict_corpus = [
            {
                "id": p.id,
                "title": p.title or "",
                "abstract": p.abstract or "",
                "venue": p.venue or "",
                "citations": p.citation_count or 0,
                "year": p.year or 2026,
            }
            for p in papers
        ]

        payload = {
            "dict_corpus": dict_corpus,
            "dynamic_config": dynamic_config
        }

        try:
            logger.info("Sending %d papers to Colab GPU for reranking...", len(papers))
            response = requests.post(self.colab_url, json=payload, timeout=180)
            response.raise_for_status()
            ranked_dicts = response.json().get("ranked_papers", [])

            reordered_papers: list[PaperSummary] = []
            for rd in ranked_dicts:
                p_id = rd.get("id")
                if p_id in paper_map:
                    reordered_papers.append(paper_map[p_id])

            # Append any unranked papers at the end to prevent data loss
            seen_ids = {p.id for p in reordered_papers}
            for p in papers:
                if p.id not in seen_ids:
                    reordered_papers.append(p)

            logger.info("Successfully reranked %d papers via GPU.", len(reordered_papers))
            
            # Return full reordered list if top_k is None, else slice top_k
            return reordered_papers[:top_k] if top_k else reordered_papers

        except Exception as e:
            logger.exception("Colab GPU Reranker failed or timed out: %s. Returning fallback list.", e)
            return papers[:top_k] if top_k else papers