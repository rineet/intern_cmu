from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:

    # ==========================================================
    # Application
    # ==========================================================

    app_name: str = "Research Finder"

    api_prefix: str = "/api"

    api_base_url: str = field(
        default_factory=lambda: os.getenv(
            "API_BASE_URL",
            "http://localhost:8000"
        )
    )

    frontend_origin: str = field(
        default_factory=lambda: os.getenv(
            "FRONTEND_ORIGIN",
            "http://localhost:5173"
        )
    )

    # ==========================================================
    # Database
    # ==========================================================

    database_path: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "DATABASE_PATH",
                str(
                    Path(__file__)
                    .resolve()
                    .parents[3]
                    / "data"
                    / "research_finder.duckdb"
                ),
            )
        )
    )

    # ==========================================================
    # Gemini
    # ==========================================================

    gemini_api_key: str | None = field(
        default_factory=lambda:
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    gemini_model: str = field(
        default_factory=lambda: os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash"
        )
    )

    gemini_timeout_seconds: float = field(
        default_factory=lambda: float(
            os.getenv(
                "GEMINI_TIMEOUT_SECONDS",
                "30"
            )
        )
    )

    # ==========================================================
    # Search
    # ==========================================================

    search_timeout_seconds: float = field(
        default_factory=lambda: float(
            os.getenv(
                "SEARCH_TIMEOUT_SECONDS",
                "20"
            )
        )
    )

    search_limit_per_source: int = field(
        default_factory=lambda: int(
            os.getenv(
                "SEARCH_LIMIT_PER_SOURCE",
                "10"
            )
        )
    )

    # ==========================================================
    # Keyword Expansion
    # ==========================================================

    max_expanded_terms: int = field(
        default_factory=lambda: int(
            os.getenv(
                "MAX_EXPANDED_TERMS",
                "15"
            )
        )
    )

    # Number of generated search queries
    max_search_queries: int = field(
        default_factory=lambda: int(
            os.getenv(
                "MAX_SEARCH_QUERIES",
                "10"
            )
        )
    )

    # ==========================================================
    # Reranking
    # ==========================================================

    rerank_top_k: int = field(
        default_factory=lambda: int(
            os.getenv(
                "RERANK_TOP_K",
                "30"
            )
        )
    )

    # ==========================================================
    # Caching
    # ==========================================================

    cache_enabled: bool = field(
        default_factory=lambda:
        os.getenv(
            "CACHE_ENABLED",
            "true"
        ).lower() == "true"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()