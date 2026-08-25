from __future__ import annotations

import logging
import requests
import time
from ..core.config import Settings
from ..schemas import PaperSummary

logger = logging.getLogger(__name__)


class RerankerService:
    """Delegates heavy model execution to the Google Colab GPU microservice."""

    def __init__(self, settings: Settings):
        self.settings = settings
        # Strip trailing slashes just in case the .env file has one
        self.colab_url = settings.colab_reranker_url.rstrip('/')
        logger.info(f"🔧 RerankerService initialized. Base Target URL is: {self.colab_url}")

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
            logger.info("Sending %d papers to Colab GPU for async reranking...", len(papers))
            
            # 1. Start the job
            async_url = f"{self.colab_url}/rerank_async"
            response = requests.post(async_url, json=payload, timeout=60)
            response.raise_for_status()
            
            job_id = response.json()["job_id"]
            logger.info(f"GPU job created: {job_id}. Waiting for completion...")
            
            # 2. Poll for completion with a safety timeout (Max 60 polls = 5 minutes)
            status_url = f"{self.colab_url}/rerank_status/{job_id}"
            ranked_dicts = []
            
            max_polls = 60  # 60 * 5 seconds = 300 seconds (5 minutes max)
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(5)
                poll_count += 1
                
                try:
                    status_res = requests.get(status_url, timeout=10)
                    status_res.raise_for_status()
                    data = status_res.json()
                    
                    if data.get("status") == "completed":
                        ranked_dicts = data.get("result", [])
                        logger.info("GPU processing complete!")
                        break
                    elif data.get("status") == "failed":
                        error_msg = data.get('error', 'Unknown Error')
                        logger.error(f"GPU processing failed on Colab side: {error_msg}")
                        return papers[:top_k] if top_k else papers
                    elif data.get("status") == "not_found":
                        logger.error("GPU lost the job. Returning fallback list.")
                        return papers[:top_k] if top_k else papers
                    
                    logger.info("GPU is still crunching numbers... poll %d/%d", poll_count, max_polls)
                except requests.RequestException as poll_err:
                    logger.warning(f"Temporary polling error ({poll_err}). Retrying...")

            if not ranked_dicts and poll_count >= max_polls:
                logger.error("GPU job timed out after 5 minutes. Returning fallback list.")
                return papers[:top_k] if top_k else papers

            # 3. Process the results back into PaperSummary objects
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
            return reordered_papers[:top_k] if top_k else reordered_papers

        except Exception as e:
            logger.exception("Colab GPU Reranker failed or timed out: %s. Returning fallback list.", e)
            return papers[:top_k] if top_k else papers