from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ..repositories.search_repository import SearchRepository
from ..schemas import ApiMessage, KeywordSearchResponse, PaperDetail, SearchHistoryEntry, SearchRequest, SearchResponse
from ..services.search_service import SearchService


router = APIRouter()


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service


def get_repository(request: Request) -> SearchRepository:
    return request.app.state.repository


@router.post("/api/search", response_model=SearchResponse)
@router.post("/search", response_model=SearchResponse)
async def search_papers(payload: SearchRequest, search_service: SearchService = Depends(get_search_service)) -> SearchResponse:
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query required")
    return await search_service.search(query, timeline_months=payload.timeline_months)


@router.get("/api/papers", response_model=list[PaperDetail])
@router.get("/papers", response_model=list[PaperDetail])
def list_papers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: SearchRepository = Depends(get_repository),
) -> list[PaperDetail]:
    return repository.list_papers(limit=limit, offset=offset)


@router.get("/api/papers/{paper_id}", response_model=PaperDetail)
@router.get("/papers/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: str, repository: SearchRepository = Depends(get_repository)) -> PaperDetail:
    paper = repository.get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="paper not found")
    return paper


@router.get("/api/search-history", response_model=list[SearchHistoryEntry])
@router.get("/search-history", response_model=list[SearchHistoryEntry])
def get_search_history(
    limit: int = Query(default=25, ge=1, le=100),
    repository: SearchRepository = Depends(get_repository),
) -> list[SearchHistoryEntry]:
    return repository.list_search_history(limit=limit)


@router.get("/health", response_model=ApiMessage)
def health() -> ApiMessage:
    return ApiMessage(message="ok")
