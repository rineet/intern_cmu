from __future__ import annotations

import os
import json
import time
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class GeminiBusyException(Exception):
    """Raised when Gemini API remains rate-limited or busy after exhausting retries."""
    pass


class GeminiSeedSelector:
    """Domain-agnostic Gemini Re-Ranker for identifying paradigmatically diverse seed papers."""

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.5-flash"):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable or api_key parameter is required.")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def _call_gemini_with_backoff(self, prompt: str, schema: type, max_retries: int = 3) -> str:
        """Executes a Gemini API call with exponential backoff retry logic and strict determinism."""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        # Force greedy decoding for strict determinism
                        temperature=0.0,
                        top_k=1,
                    ),
                )
                if response and response.text:
                    return response.text
                raise ValueError("Empty response from Gemini API.")
            except Exception as e:
                logger.warning(f"Gemini API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    backoff = 2 ** (attempt + 1)  # 2s, 4s, 8s...
                    logger.info(f"Retrying Gemini API in {backoff} seconds...")
                    time.sleep(backoff)
                else:
                    logger.error("Exhausted all retries for Gemini API.")
                    raise GeminiBusyException("Gemini is kinda busy, please try again later.") from e

    def select_seeds(
        self, 
        papers_json: list[dict], 
        query: str, 
        top_n: int = 10,
        save_path: str | None = None
    ) -> list[dict]:
        """Selects top N diverse seed papers directly evaluating ALL candidates."""
        if len(papers_json) <= top_n:
            self._log_selection(papers_json)
            if save_path:
                self._save_to_file(save_path, papers_json)
            return papers_json

        # REMOVED CAP: Processing the entire papers_json array directly
        candidate_summaries = []
        id_map = {} 
        
        for idx, p in enumerate(papers_json):
            id_map[idx] = p
            candidate_summaries.append({
                "internal_id": idx,
                "title": p.get("title"),
                # Smart Truncation: 2000 chars allows most full abstracts, blocking massive anomalies
                "abstract": (p.get("abstract") or "")[:2000], 
                "year": p.get("year"),
                "citations": p.get("citation_count", 0)
            })

        prompt = f"""
You are an expert academic literature curator. Your task is to select seed papers to expand a citation graph (via forward citations and backward references) for a specific research topic.

USER RESEARCH QUERY / PROBLEM STATEMENT:
"{query}"

SELECTION INSTRUCTIONS:
1. Analyze the user query to understand the overall research domain and core problem.
2. Examine the candidate papers and dynamically infer the key sub-topics, methodological approaches, and technical paradigms present in this specific pool.
3. Select EXACTLY {top_n} seed papers that maximize overall citation graph yield across the topic space:
   - Include comprehensive survey/review papers (broad citation hubs).
   - Include key benchmark or dataset papers.
   - Include seminal/foundational papers representing DISTINCT technical paradigms.
4. Ensure HIGH DIVERSITY: Avoid selecting multiple papers that use near-identical methods.

CANDIDATE PAPERS:
{json.dumps(candidate_summaries, indent=2)}

OUTPUT REQUIREMENT:
Return a JSON list of EXACTLY {top_n} integer `internal_id` values corresponding to your selections.
"""

        try:
            raw_response = self._call_gemini_with_backoff(prompt, schema=list[int])
            selected_internal_ids = json.loads(raw_response)
            
            selected_papers = []
            for paper_id in selected_internal_ids:
                if paper_id in id_map and len(selected_papers) < top_n:
                    selected_papers.append(id_map[paper_id])

            self._log_selection(selected_papers)

            if save_path and selected_papers:
                self._save_to_file(save_path, selected_papers)

            return selected_papers

        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse Gemini output as JSON. Raw output: {raw_response}")
            return papers_json[:top_n]

    def _log_selection(self, papers: list[dict]) -> None:
        """Helper function to cleanly log the selected papers to the terminal."""
        if not papers:
            logger.warning("No papers were selected.")
            return

        display_summary = [
            {
                "title": p.get("title", "Unknown Title"), 
                "year": p.get("year", "N/A"), 
                "citations": p.get("citation_count", 0)
            } 
            for p in papers
        ]
        
        formatted_summary = json.dumps(display_summary, indent=2)
        logger.info(f"Successfully selected {len(papers)} seed papers:\n{formatted_summary}")

    @staticmethod
    def _save_to_file(file_path: str, papers: list[dict]) -> None:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(papers, f, indent=2, ensure_ascii=False)
            logger.info("Saved %d seed papers to '%s'", len(papers), file_path)
        except Exception as e:
            logger.error("Failed to save seeds to file '%s': %s", file_path, e)