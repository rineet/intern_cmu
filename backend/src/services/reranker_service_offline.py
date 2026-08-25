from __future__ import annotations

import logging
import math
import re
import numpy as np
import torch
from scipy.special import expit
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

from ..core.config import Settings
from ..schemas import PaperSummary
from .constants import TOP_VENUES

logger = logging.getLogger(__name__)


class AcademicRetrievalPipeline:
    def __init__(
        self,
        bi_encoder_name: str = "Alibaba-NLP/gte-modernbert-base",
        cross_encoder_name: str = "BAAI/bge-reranker-v2-m3",
        device: str | None = None,
    ):
        # Auto-detect CUDA GPU locally
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info("Using local device for inference: %s", device)
        self.bi_encoder = SentenceTransformer(bi_encoder_name, device=device)
        self.cross_encoder = CrossEncoder(cross_encoder_name, max_length=512, device=device)

        self.corpus_papers: list[dict] = []
        self.bm25: BM25Okapi | None = None
        self.corpus_embeddings: np.ndarray | None = None
        self.TOP_VENUES = TOP_VENUES

    @staticmethod
    def _camel_case_tokenize(text: str) -> list[str]:
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        return re.findall(r"\b\w+\b", text.lower())

    def index_corpus(self, papers: list[dict], batch_size: int = 32) -> None:
        self.corpus_papers = papers
        tokenized_corpus = [
            self._camel_case_tokenize(f"{p.get('title', '')} {p.get('abstract', '')}")
            for p in self.corpus_papers
        ]
        self.bm25 = BM25Okapi(tokenized_corpus)

        corpus_texts = [
            f"Title: {p.get('title', '')} | Abstract: {p.get('abstract', '')}"
            for p in self.corpus_papers
        ]
        self.corpus_embeddings = self.bi_encoder.encode(
            corpus_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def _stage1_hybrid_search(self, dynamic_config: dict, rrf_k: int = 60) -> list[dict]:
        n_papers = len(self.corpus_papers)
        rrf_scores = np.zeros(n_papers)
        all_aspect_queries = dynamic_config.get("DYNAMIC_ASPECTS", []) + [dynamic_config.get("CLEAN_INTENT_QUERY", "")]

        for q_str in all_aspect_queries:
            q_tokens = self._camel_case_tokenize(q_str)
            bm25_doc_scores = self.bm25.get_scores(q_tokens)
            bm25_ranks = np.argsort(-bm25_doc_scores)

            q_emb = self.bi_encoder.encode([q_str], normalize_embeddings=True)
            dense_doc_scores = np.dot(self.corpus_embeddings, q_emb.T).squeeze()
            dense_ranks = np.argsort(-dense_doc_scores)

            for rank_idx, doc_idx in enumerate(bm25_ranks):
                rrf_scores[doc_idx] += 1.0 / (rrf_k + rank_idx + 1)
            for rank_idx, doc_idx in enumerate(dense_ranks):
                rrf_scores[doc_idx] += 1.0 / (rrf_k + rank_idx + 1)

        stage1_final_scores = np.copy(rrf_scores)
        baseline_models = [m.lower() for m in dynamic_config.get("BASELINE_MODELS", [])]
        penalty_terms = [p.lower() for p in dynamic_config.get("PENALTY_TERMS", [])]

        for i, p in enumerate(self.corpus_papers):
            t_clean = p.get("title", "").lower()
            a_clean = p.get("abstract", "").lower()
            v_clean = str(p.get("venue", "")).lower()

            if any(m in t_clean for m in baseline_models if len(m) > 2):
                stage1_final_scores[i] += 0.030

            c_count = p.get("citations", 0)
            if c_count > 0:
                stage1_final_scores[i] += min(0.020, math.log10(c_count + 1) * 0.005)

            if any(pt in a_clean or pt in t_clean for pt in penalty_terms):
                stage1_final_scores[i] -= 0.025

            if any(v in v_clean for v in self.TOP_VENUES):
                stage1_final_scores[i] += 0.015

            try:
                year = int(p.get("year", 2026))
            except (ValueError, TypeError):
                year = 2026

            age = max(0, 2026 - year)
            stage1_final_scores[i] -= min(0.020, age * 0.002)

        scored_papers = []
        for i, p in enumerate(self.corpus_papers):
            paper_copy = dict(p)
            paper_copy["stage1_score"] = float(stage1_final_scores[i])
            scored_papers.append(paper_copy)

        return sorted(scored_papers, key=lambda x: x["stage1_score"], reverse=True)

    def _stage2_additive_rerank(self, top_candidates: list[dict], dynamic_config: dict, alpha: float = 0.70) -> list[dict]:
        all_aspect_queries = dynamic_config.get("DYNAMIC_ASPECTS", []) + [dynamic_config.get("CLEAN_INTENT_QUERY", "")]
        ce_max_p_scores = []

        for paper in top_candidates:
            doc_text = f"Title: {paper.get('title', '')} | Abstract: {paper.get('abstract', '')}"
            pairs = [[aspect_q, doc_text] for aspect_q in all_aspect_queries]

            raw_logits = self.cross_encoder.predict(pairs, show_progress_bar=False)
            probs = expit(raw_logits)
            max_score = float(np.max(probs))
            ce_max_p_scores.append(max_score)
            paper["ce_score"] = max_score

        s1_raw = np.array([p["stage1_score"] for p in top_candidates])
        s1_min, s1_max = s1_raw.min(), s1_raw.max()
        s1_norm = (s1_raw - s1_min) / (s1_max - s1_min + 1e-8)

        ce_norm = np.array(ce_max_p_scores)
        blended_scores = (alpha * ce_norm) + ((1.0 - alpha) * s1_norm)

        for idx, p in enumerate(top_candidates):
            p["final_blended_score"] = float(blended_scores[idx])

        return sorted(top_candidates, key=lambda x: x["final_blended_score"], reverse=True)

    def retrieve(self, dynamic_config: dict, top_k_stage1: int = 600, alpha: float = 0.70) -> list[dict]:
        if not self.corpus_papers:
            return []
        stage1_ranked = self._stage1_hybrid_search(dynamic_config)
        top_candidates = stage1_ranked[:top_k_stage1]
        remainder = stage1_ranked[top_k_stage1:]
        stage2_ranked = self._stage2_additive_rerank(top_candidates, dynamic_config, alpha=alpha)
        return stage2_ranked + remainder


class RerankerService:
    def __init__(self, settings: Settings):
        self.settings = settings
        bi_encoder = getattr(settings, "bi_encoder_model", "Alibaba-NLP/gte-modernbert-base")
        cross_encoder = getattr(settings, "cross_encoder_model", "BAAI/bge-reranker-v2-m3")

        # Runs locally on GPU via PyTorch CUDA
        self.pipeline = AcademicRetrievalPipeline(
            bi_encoder_name=bi_encoder,
            cross_encoder_name=cross_encoder,
        )

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

        # Execute locally on GPU
        self.pipeline.index_corpus(dict_corpus)
        ranked_dicts = self.pipeline.retrieve(dynamic_config, top_k_stage1=min(600, len(papers)))

        reordered_papers: list[PaperSummary] = []
        for rd in ranked_dicts:
            p_id = rd["id"]
            if p_id in paper_map:
                reordered_papers.append(paper_map[p_id])

        return reordered_papers[:top_k] if top_k else reordered_papers
