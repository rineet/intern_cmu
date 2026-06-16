from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ==========================================================
# Keyword Expansion
# ==========================================================

class ExpandedKeywords(BaseModel):
    canonical_terms: list[str] = Field(default_factory=list)
    acronyms: list[str] = Field(default_factory=list)
    expanded_terms: list[str] = Field(default_factory=list)
    related_terms: list[str] = Field(default_factory=list)
    research_domains: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)

# ==========================================================
# Search Request
# ==========================================================

class SearchRequest(BaseModel):
    query: str
    timeline_months: int | None = Field(default=None, ge=1, le=120)

# ==========================================================
# Paper Models
# ==========================================================

class PaperBase(BaseModel):
    id: str
    title: str
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    venue: str = ""
    year: int = 0
    source: str = ""
    pdf_url: str = ""
    doi: str = ""
    url: str = ""
    citation_count: int = 0
    relevance_score: float = 0.0
    published_at: datetime | None = None

class PaperSummary(PaperBase):
    model_config = ConfigDict(from_attributes=True)

class PaperDetail(PaperSummary):
    query_id: str = ""
    created_at: datetime | None = None

# ==========================================================
# Search Responses
# ==========================================================

class SearchResponse(BaseModel):
    search_id: str
    query: str
    timeline_months: int | None = None
    expanded_keywords: ExpandedKeywords
    papers: list[PaperSummary] = Field(default_factory=list)
    created_at: datetime

class SearchHistoryEntry(BaseModel):
    id: str
    original_query: str
    expanded_keywords: ExpandedKeywords
    created_at: datetime
    paper_count: int = 0

class SearchStorePayload(BaseModel):
    query: str
    expanded_keywords: ExpandedKeywords
    papers: list[PaperSummary] = Field(default_factory=list)

# ==========================================================
# API Responses
# ==========================================================

class ApiMessage(BaseModel):
    message: str

class KeywordSearchResponse(BaseModel):
    query: str
    expanded_keywords: ExpandedKeywords
    papers: list[PaperSummary]

class ErrorResponse(BaseModel):
    detail: str
