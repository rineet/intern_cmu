from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import os
from typing import TypeVar, Type, Any

from dotenv import load_dotenv

# ==============================================================================
# Smart .env Resolver
# Resolves working directory mismatches by checking root & parent paths
# ==============================================================================
def _load_env() -> None:
    config_dir = Path(__file__).resolve().parent
    candidate_paths = [
        Path.cwd() / ".env",
        config_dir / ".env",
        config_dir.parent / ".env",
        config_dir.parent.parent / ".env",
        config_dir.parent.parent.parent / ".env",
    ]
    
    for path in candidate_paths:
        if path.is_file():
            load_dotenv(dotenv_path=path, override=True)
            break

_load_env()

T = TypeVar("T")

def _get_env(key: str, default: T = None, cast: Type[T] = str) -> T | Any:
    val = os.getenv(key)
    if val is None or val == "":
        return default
    if cast is bool:
        return val.lower() in ("true", "1", "yes", "on")
    try:
        return cast(val)
    except (ValueError, TypeError):
        return default


# ==============================================================================
# Application Settings
# ==============================================================================
@dataclass(frozen=True)
class Settings:

    # --- Application ---
    app_name: str = "Research Finder"
    api_prefix: str = "/api"
    api_base_url: str = field(
        default_factory=lambda: _get_env("API_BASE_URL", "http://localhost:8000")
    )
    frontend_origin: str = field(
        default_factory=lambda: _get_env("FRONTEND_ORIGIN", "http://localhost:5173")
    )

    # --- Database ---
    database_path: Path = field(
        default_factory=lambda: Path(
            _get_env(
                "DATABASE_PATH",
                str(Path(__file__).resolve().parents[3] / "data" / "research_finder.duckdb"),
            )
        )
    )

    # --- Gemini ---
    gemini_api_key: str | None = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
    gemini_model: str = field(
        default_factory=lambda: _get_env("GEMINI_MODEL", "gemini-2.5-flash")
    )
    gemini_timeout_seconds: float = field(
        default_factory=lambda: _get_env("GEMINI_TIMEOUT_SECONDS", 30.0, float)
    )

    # --- External APIs ---
    semantic_scholar_api_key: str | None = field(
        default_factory=lambda: _get_env("SEMANTIC_SCHOLAR_API_KEY")
    )
    OpenAlex_api_key: str | None = field(
        default_factory=lambda: _get_env("OPENALEX_API_KEY") or _get_env("OpenAlex_api_key")
    )
    MAIL: str | None = field(
        default_factory=lambda: _get_env("MAIL")
    )

    # --- Search ---
    search_timeout_seconds: float = field(
        default_factory=lambda: _get_env("SEARCH_TIMEOUT_SECONDS", 20.0, float)
    )
    search_limit_per_source: int = field(
        default_factory=lambda: _get_env("SEARCH_LIMIT_PER_SOURCE", 15, int)
    )

    # --- Keyword Expansion ---
    max_expanded_terms: int = field(
        default_factory=lambda: _get_env("MAX_EXPANDED_TERMS", 15, int)
    )
    max_search_queries: int = field(
        default_factory=lambda: _get_env("MAX_SEARCH_QUERIES", 10, int)
    )

    # --- Reranking & GPU Offloading ---
    reranker_mode: str = field(
        default_factory=lambda: _get_env("RERANKER_MODE", "remote").lower()
    )
    rerank_top_k: int = field(
        default_factory=lambda: _get_env("RERANK_TOP_K", 50, int)
    )
    colab_reranker_url: str = field(
        default_factory=lambda: _get_env("COLAB_RERANKER_URL", "http://localhost:8001")
    )
    bi_encoder_model: str = field(
        default_factory=lambda: _get_env("BI_ENCODER_MODEL", "Alibaba-NLP/gte-modernbert-base")
    )
    cross_encoder_model: str = field(
        default_factory=lambda: _get_env("CROSS_ENCODER_MODEL", "BAAI/bge-reranker-v2-m3")
    )

    # --- Caching ---
    cache_enabled: bool = field(
        default_factory=lambda: _get_env("CACHE_ENABLED", True, bool)
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
