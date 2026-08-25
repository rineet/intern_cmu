from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SearchRecord(Base):
    __tablename__ = "searches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    expanded_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class PaperRecord(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    paper_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    abstract: Mapped[str] = mapped_column(Text, nullable=False, default="")
    authors: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    venue: Mapped[str] = mapped_column(Text, nullable=False, default="")
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pdf_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    doi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    query_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # --- NEW FIELDS ADDED ---
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)