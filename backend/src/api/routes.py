from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, BackgroundTasks

from ..repositories.search_repository import SearchRepository
from ..schemas import ApiMessage, KeywordSearchResponse, PaperDetail, SearchHistoryEntry, SearchRequest, SearchResponse
from ..services.search_service import SearchService
from ..services.semantic_scholar_service import SemanticScholarService
import uuid
# In-memory store to hold the status of background searches
search_jobs = {}

async def run_search_background(job_id: str, query: str, timeline_months: int | None, search_service: SearchService):
    try:
        # Run the massive 15-minute GPU search
        result = await search_service.search(query, timeline_months=timeline_months)
        search_jobs[job_id]["status"] = "completed"
        search_jobs[job_id]["result"] = result
    except Exception as e:
        search_jobs[job_id]["status"] = "failed"
        search_jobs[job_id]["error"] = str(e)


router = APIRouter()


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service


def get_repository(request: Request) -> SearchRepository:
    return request.app.state.repository


@router.post("/api/search")
@router.post("/search")
async def start_search_papers(
    payload: SearchRequest, 
    background_tasks: BackgroundTasks, 
    search_service: SearchService = Depends(get_search_service)
):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query required")
    
    # 1. Create a unique ticket (job ID)
    job_id = str(uuid.uuid4())
    search_jobs[job_id] = {"status": "processing", "result": None, "error": None}
    
    # 2. Tell FastAPI to run the heavy function in the background
    background_tasks.add_task(run_search_background, job_id, query, payload.timeline_months, search_service)
    
    # 3. Instantly return the ticket to the frontend
    return {"job_id": job_id, "status": "processing"}


@router.get("/api/search/status/{job_id}")
@router.get("/search/status/{job_id}")
def get_search_status(job_id: str):
    job = search_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    if job["status"] == "completed":
        result = job["result"]
        # Clean up memory so the dictionary doesn't get huge
        del search_jobs[job_id]
        return {"status": "completed", "result": result}
    elif job["status"] == "failed":
        error = job["error"]
        del search_jobs[job_id]
        return {"status": "failed", "error": error}
    else:
        return {"status": "processing"}


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
