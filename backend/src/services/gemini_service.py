from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import requests

from ..core.config import Settings
from ..schemas import ExpandedKeywords

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class GeminiKeywordService:
    settings: Settings

    def expand(self, query: str) -> ExpandedKeywords:
        query = query.strip()

        fallback = self._fallback_keywords(query)

        if not self.settings.gemini_api_key:
            logger.warning("No Gemini API key configured")
            return fallback

        try:
            payload = self._build_payload(query)

            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.settings.gemini_model}:generateContent",
                params={"key": self.settings.gemini_api_key},
                json=payload,
                timeout=self.settings.gemini_timeout_seconds,
            )

            response.raise_for_status()

            data = response.json()

            text = self._extract_text(data)


            parsed = self._parse_response(text)

            if not parsed:
                logger.warning(
                    "Gemini response could not be parsed. Using fallback."
                )
                return fallback

            keywords = self._normalize_keywords(parsed)

            if (
                keywords.canonical_terms
                or keywords.related_terms
                or keywords.search_queries
            ):
                return keywords

            return fallback

        except Exception:
            logger.exception("Gemini keyword expansion failed")
            return fallback

    def _build_payload(self, query: str) -> dict:
        prompt=f"""
You are an expert academic research assistant.

Your task is to expand research queries into academic search keywords.

Return ONLY valid JSON.

Example 1

Query:
privacy preserving fingerprint matching

Output:
{{
  "canonical_terms": [
    "privacy-preserving fingerprint matching",
    "biometric authentication"
  ],
  "acronyms": [
    "psi"
  ],
  "expanded_terms": [
    "private set intersection"
  ],
  "related_terms": [
    "secure biometric matching",
    "privacy-preserving authentication"
  ],
  "research_domains": [
    "cryptography",
    "computer security",
    "biometrics"
  ],
  "search_queries": [
    "privacy preserving fingerprint matching",
    "private set intersection biometric authentication"
  ]
}}

Example 2

Query:
breast cancer detection using deep learning

Output:
{{
  "canonical_terms": [
    "breast cancer detection",
    "deep learning"
  ],
  "acronyms": [
    "cnn"
  ],
  "expanded_terms": [
    "convolutional neural network"
  ],
  "related_terms": [
    "mammography classification",
    "medical image analysis"
  ],
  "research_domains": [
    "oncology",
    "computer vision",
    "medical imaging"
  ],
  "search_queries": [
    "deep learning breast cancer detection",
    "cnn mammography classification"
  ]
}}

Now process:

Query:
{query}

Return ONLY JSON.
Do not include markdown.
Do not include explanations.
Do not wrap the JSON in ```json fences.
"""
        return {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "canonical_terms": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        },
                        "acronyms": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        },
                        "expanded_terms": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        },
                        "related_terms": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        },
                        "research_domains": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        },
                        "search_queries": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        }
                    },
                    "required": [
                        "canonical_terms",
                        "acronyms",
                        "expanded_terms",
                        "related_terms",
                        "research_domains",
                        "search_queries"
                    ]
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
            canonical_terms=self._clean(
                payload.get("canonical_terms", [])
            ),
            acronyms=self._clean(
                payload.get("acronyms", [])
            ),
            expanded_terms=self._clean(
                payload.get("expanded_terms", [])
            ),
            related_terms=self._clean(
                payload.get("related_terms", [])
            ),
            research_domains=self._clean(
                payload.get("research_domains", [])
            ),
            search_queries=self._clean(
                payload.get("search_queries", [])
            ),
        )

    def _clean(self, values: object) -> list[str]:
        
        if not isinstance(values, list):
            return []

        cleaned: list[str] = []
        seen: set[str] = set()

        for value in values:
            item = " ".join(
                str(value).strip().lower().split()
            )

            if not item:
                continue

            if item in seen:
                continue
            if len(item) <= 2:
                continue
            seen.add(item)
            cleaned.append(item)

        return cleaned[: self.settings.max_expanded_terms]

    def _fallback_keywords(
        self,
        query: str,
    ) -> ExpandedKeywords:
        return ExpandedKeywords(
            canonical_terms=[query.lower()],
            related_terms=[],
            search_queries=[query],
        )

