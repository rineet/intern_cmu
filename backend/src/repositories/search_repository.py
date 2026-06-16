from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable
from uuid import uuid4

from sqlalchemy import desc, select

from ..db.models import PaperRecord, SearchRecord
from ..db.session import get_session
from ..schemas import ExpandedKeywords, PaperDetail, PaperSummary, SearchHistoryEntry


class SearchRepository:
    def create_search(self, query: str, expanded_keywords: ExpandedKeywords) -> SearchRecord:
        record = SearchRecord(
            id=str(uuid4()),
            original_query=query,
            expanded_keywords=expanded_keywords.model_dump_json(),
            created_at=datetime.utcnow(),
        )
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return record

    def save_papers(self, query_id: str, papers: Iterable[PaperSummary]) -> list[PaperRecord]:
        records: list[PaperRecord] = []
        now = datetime.utcnow()
        with get_session() as session:
            for paper in papers:
                record = PaperRecord(
                    paper_id=paper.id,
                    title=paper.title,
                    abstract=paper.abstract,
                    authors=json.dumps(paper.authors),
                    venue=paper.venue,
                    year=paper.year,
                    source=paper.source,
                    pdf_url=paper.pdf_url,
                    doi=paper.doi,
                    query_id=query_id,
                    created_at=now,
                )
                session.add(record)
                records.append(record)
            session.commit()
            for record in records:
                session.refresh(record)
        return records

    def list_papers(self, limit: int = 50, offset: int = 0) -> list[PaperDetail]:
        with get_session() as session:
            stmt = select(PaperRecord).order_by(desc(PaperRecord.created_at)).limit(limit).offset(offset)
            rows = session.execute(stmt).scalars().all()
        return [self._to_detail(row) for row in rows]

    def get_paper(self, paper_id: str) -> PaperDetail | None:
        with get_session() as session:
            stmt = select(PaperRecord).where(PaperRecord.paper_id == paper_id).order_by(desc(PaperRecord.created_at))
            row = session.execute(stmt).scalars().first()
        return self._to_detail(row) if row else None

    def list_search_history(self, limit: int = 25) -> list[SearchHistoryEntry]:
        with get_session() as session:
            stmt = select(SearchRecord).order_by(desc(SearchRecord.created_at)).limit(limit)
            rows = session.execute(stmt).scalars().all()

        paper_counts: dict[str, int] = {}
        with get_session() as session:
            paper_rows = session.execute(select(PaperRecord.query_id)).all()
        for (query_id,) in paper_rows:
            paper_counts[query_id] = paper_counts.get(query_id, 0) + 1

        entries: list[SearchHistoryEntry] = []
        for row in rows:
            entries.append(
                SearchHistoryEntry(
                    id=row.id,
                    original_query=row.original_query,
                    expanded_keywords=ExpandedKeywords.model_validate_json(row.expanded_keywords),
                    created_at=row.created_at,
                    paper_count=paper_counts.get(row.id, 0),
                )
            )
        return entries

    @staticmethod
    def _to_detail(row: PaperRecord | None) -> PaperDetail | None:
        if row is None:
            return None
        return PaperDetail(
            id=row.paper_id,
            title=row.title,
            abstract=row.abstract,
            authors=json.loads(row.authors or "[]"),
            venue=row.venue,
            year=row.year,
            source=row.source,
            pdf_url=row.pdf_url,
            doi=row.doi,
            query_id=row.query_id,
            created_at=row.created_at,
        )