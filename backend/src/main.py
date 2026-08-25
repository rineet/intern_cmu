from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.config import get_settings
from .core.logging import configure_logging
from .db.session import initialize_database
from .repositories.search_repository import SearchRepository
from .services.gemini_service import GeminiKeywordService
from .services.paper_sources import PaperSourceService
from .services.search_service import SearchService
from .services.semantic_scholar_service import SemanticScholarService

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    app.state.repository = SearchRepository()
    app.state.search_service = SearchService(
        settings=settings,
        repository=app.state.repository,
        keyword_service=GeminiKeywordService(settings=settings),
        source_service=PaperSourceService(settings=settings),
        semantic_service = SemanticScholarService(settings=settings),
    )
    logger.info("Research Finder backend started")
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Research Finder API"}