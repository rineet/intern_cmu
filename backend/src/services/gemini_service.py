from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass

import requests

from ..core.config import Settings
from ..schemas import ExpandedKeywords

logger = logging.getLogger(__name__)

class GeminiBusyException(Exception):
    """Raised when Gemini API remains rate-limited or busy after exhausting retries."""
    pass

@dataclass(slots=True)
class GeminiKeywordService:
    settings: Settings

    def _call_api_with_backoff(self, payload: dict, max_retries: int = 3) -> dict:
        """Executes a Gemini REST API call with exponential backoff retry logic."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent"
        params = {"key": self.settings.gemini_api_key}

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    params=params,
                    json=payload,
                    timeout=self.settings.gemini_timeout_seconds,
                )
                
                # Force retry on Rate Limit or Server Errors
                if response.status_code == 429 or response.status_code >= 500:
                    raise requests.exceptions.RequestException(f"HTTP {response.status_code}: {response.text}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                logger.warning("Gemini Keyword API failed (attempt %d/%d): %s", attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    backoff = 2 ** (attempt + 1)  # 2s, 4s, 8s...
                    logger.info("Retrying Gemini Keyword API in %d seconds...", backoff)
                    time.sleep(backoff)
                else:
                    logger.error("Exhausted all retries for Gemini Keyword API.")
                    raise GeminiBusyException("Gemini is kinda busy, please try again later.") from e

    def expand(self, query: str) -> ExpandedKeywords:
        query = query.strip()
        fallback = self._fallback_keywords(query)

        if not self.settings.gemini_api_key:
            logger.warning("No Gemini API key configured")
            return fallback

        try:
            payload = self._build_payload(query)

            # Use the new backoff mechanism
            data = self._call_api_with_backoff(payload)

            text = self._extract_text(data)
            parsed = self._parse_response(text)

            if not parsed:
                logger.warning("Gemini response could not be parsed. Using fallback.")
                return fallback

            keywords = self._normalize_keywords(parsed)

            if keywords.search_queries:
                return keywords

            return fallback

        except GeminiBusyException:
            # Propagate the early-exit exception to the SearchService to abort the pipeline
            raise
        except Exception:
            logger.exception("Gemini keyword expansion failed")
            return fallback
    
    def _build_payload(self, query: str) -> dict:
        prompt = f"""
You are an expert Academic Literature Retrieval Specialist.
Your objective is to generate highly effective search queries for academic databases (e.g., OpenAlex, Semantic Scholar) based on the provided input.

INPUT:
"{query}"

(Note: The input may range from a brief concept to a complete paper abstract).

STEP 1: CONCEPTUAL DECONSTRUCTION
- Identify the core research problem, target domain, and specific methodologies.
- Extract exact field-specific terminology, standard acronyms, and critical constraints.
- If the input is long (e.g., an abstract), ignore experimental results and future work; focus only on the core contribution.

STEP 2: QUERY GENERATION STRATEGIES
Generate 10 to 15 distinct search queries. To ensure a robust citation graph (high precision and high recall), distribute your queries across these specific strategies:
1. Canonical Focus: The exact core methodology and application (the primary contribution).
2. Foundational/Survey: Terminology aimed at finding review papers, benchmarks, or state-of-the-art comparisons for this specific niche.
3. Component Isolation: Queries focusing purely on the specific algorithm, protocol, or dataset mentioned.
4. Alternative Lexicon: Academic synonyms or alternate phrasing used by parallel research communities (e.g., bridging "machine vision" and "computational imaging" if applicable).

STEP 3: STRICT SEARCH ENGINE RULES
- NO CONVERSATIONAL FILLER: Never use phrases like "papers about", "research on", or "show me".
- NO OPERATORS: Do not use boolean operators (AND, OR, NOT), quotes, or wildcards (*).
- KEYWORD DENSITY: Keep queries concise and dense (typically 3 to 8 words).
- TONE: Maintain a strict academic tone. Use the exact vocabulary researchers use in published paper titles and abstracts.
- NO DOMAIN DRIFT: Do not reduce highly specific technical tasks to generic parent disciplines. Stay within the exact research community of the input.

OUTPUT REQUIREMENT:
Return ONLY a valid JSON object matching the requested schema. Do not include markdown formatting or explanations.
"""
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                # STRICT DETERMINISM: Temperature 0.0 and Top K 1
                "temperature": 0.0, 
                "topK": 1,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "search_queries": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        }
                    },
                    "required": ["search_queries"]
                }
            },
        }

    @staticmethod
    def _extract_text(payload: dict) -> str:
        try:
            parts = payload["candidates"][0]["content"]["parts"]
            return "\n".join(
                part.get("text", "")
                for part in parts
                if part.get("text")
            )
        except Exception:
            return ""

    @staticmethod
    def _parse_response(text: str) -> dict:
        if not text:
            return {}

        text = text.strip()

        if text.startswith("```json"):
            text = text[7:]

        if text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            logger.exception("Failed to parse Gemini JSON")
            return {}

    def _normalize_keywords(self, payload: dict) -> ExpandedKeywords:
        return ExpandedKeywords(
            search_queries=self._clean(payload.get("search_queries", []))
        )

    def _clean(self, values: object) -> list[str]:
        if not isinstance(values, list):
            return []

        # STRICT DETERMINISM: Use dict to preserve exact LLM insertion order 
        # instead of a random-hashed set()
        cleaned_dict = {}

        for value in values:
            item = " ".join(str(value).strip().lower().split())

            if not item or len(item) <= 2:
                continue

            cleaned_dict[item] = None

        return list(cleaned_dict.keys())[: self.settings.max_expanded_terms]

    def _fallback_keywords(self, query: str) -> ExpandedKeywords:
        return ExpandedKeywords(
            search_queries=[query],
        )