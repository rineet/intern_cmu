from __future__ import annotations

import os
import json
import time
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class GeminiConfigService:
    """Service to generate dynamic hybrid search configurations using Gemini."""

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def generate_config(self, query: str, max_retries: int = 3) -> dict:
        """Calls Gemini to deconstruct the query into aspects, baselines, and penalty terms."""
        
        # Using the exact prompt you provided, with {query} dynamically injected
        prompt = f"""
You are an expert Information Retrieval (IR) and Search Engine Optimization system architect.
Your task is to analyze the provided research paper abstract. First, deduce the overarching academic research domain. Then, generate a JSON configuration payload to drive an automated, multi-stage hybrid retrieval pipeline (BM25 + Bi-Encoder + Cross-Encoder) for retrieving relevant literature in that domain.

CRITICAL RULES FOR "DYNAMIC_ASPECTS" (Aspect Budget Ratio = 5 : 2):
To prevent query overfitting and ensure high Stage 1 recall across all benchmark targets, you MUST generate exactly 7 cohesive, multi-term technical phrase aspects:
Aspects 1–5 (Broad Field Coverage - 70%): MUST cover the overarching domain's core algorithmic spectrum (e.g., sequence/neural modeling, classical/statistical baselines, transformer/self-supervised methods, parser-free/raw text representations, graph/topological representations).
Aspects 6–7 (Paper Novelty - 30%): Focus strictly on the specific novel mechanisms, architectures, or goals introduced in the input abstract.

FORMATTING RULE FOR ASPECTS:
Write short, dense, multi-term technical phrases (3–6 keywords per string).
DO NOT use conversational filler words (BAN: "a", "an", "the", "method for", "based on", "using", "approach to", "vs", "framework").

CRITICAL RULES FOR "BASELINE_MODELS":
You MUST extract 20+ model names, system names, algorithms, AND short paper acronyms common in this research domain.
IMPORTANT: Include both classical benchmark tools AND modern paper acronyms.

Input Abstract:
"{query}"

Output JSON Format:
Return ONLY a valid JSON object matching this structure:
{{
"DYNAMIC_ASPECTS": [
"Aspect 1: Broad domain core & sequence prediction keywords",
"Aspect 2: Broad classical statistical & invariant baseline keywords",
"Aspect 3: Broad transformer & self-supervised language model keywords",
"Aspect 4: Broad graph, topology, or structure keywords",
"Aspect 5: Broad parser-free or raw representation keywords",
"Aspect 6: Input abstract novel mechanism keywords",
"Aspect 7: Input abstract target goal & deployment keywords"
],
"CLEAN_INTENT_QUERY": "A concise, high-density query blending the overarching domain with the abstract's specific angle for cross-encoder reranking.",
"PENALTY_TERMS": [
"List of terms indicating unwanted paradigms based on the abstract's explicit claims"
],
"BASELINE_MODELS": [
"List of 20 classic systems, tools, AND short paper acronyms in this domain."
]
}}
"""
        # Define the exact JSON schema matching your required output[cite: 1]
        schema = {
            "type": "OBJECT",
            "properties": {
                "DYNAMIC_ASPECTS": {"type": "ARRAY", "items": {"type": "STRING"}},
                "CLEAN_INTENT_QUERY": {"type": "STRING"},
                "PENALTY_TERMS": {"type": "ARRAY", "items": {"type": "STRING"}},
                "BASELINE_MODELS": {"type": "ARRAY", "items": {"type": "STRING"}}
            },
            "required": ["DYNAMIC_ASPECTS", "CLEAN_INTENT_QUERY", "PENALTY_TERMS", "BASELINE_MODELS"]
        }

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.0, # Force greedy decoding for strict determinism[cite: 1]
                        top_k=1,         # Force greedy decoding for strict determinism[cite: 1]
                    ),
                )
                if response and response.text:
                    return json.loads(response.text)
                raise ValueError("Empty response from Gemini API.")
            except Exception as e:
                logger.warning(f"Config API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    backoff = 2 ** (attempt + 1)
                    time.sleep(backoff)
                else:
                    logger.error("Exhausted all retries for Gemini Config API.")
                    # Provide a safe fallback if Gemini completely fails
                    return {
                        "DYNAMIC_ASPECTS": [query],
                        "CLEAN_INTENT_QUERY": query,
                        "PENALTY_TERMS": [],
                        "BASELINE_MODELS": []
                    }

    def save_config_to_json(self, config_data: dict, filepath: str = "config_output.json") -> None:
        """Saves the dynamic aspects, penalty terms, and baseline models to a JSON file."""
        # Extract only the requested fields
        data_to_save = {
            "DYNAMIC_ASPECTS": config_data.get("DYNAMIC_ASPECTS", []),
            "PENALTY_TERMS": config_data.get("PENALTY_TERMS", []),
            "BASELINE_MODELS": config_data.get("BASELINE_MODELS", [])
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
            logger.info(f"Successfully saved configuration parameters to {filepath}")
        except IOError as e:
            logger.error(f"Failed to save configuration to {filepath}: {e}")