from __future__ import annotations

from difflib import SequenceMatcher

from ..schemas import PaperSummary


def normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def titles_are_similar(left: str, right: str, threshold: float = 0.92) -> bool:
    return SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio() >= threshold


def deduplicate_papers(papers: list[PaperSummary]) -> list[PaperSummary]:
    seen_dois: set[str] = set()
    deduped: list[PaperSummary] = []

    for paper in papers:
        doi = paper.doi.strip().lower()
        if doi and doi in seen_dois:
            continue

        if any(titles_are_similar(paper.title, existing.title) for existing in deduped):
            continue

        if doi:
            seen_dois.add(doi)
        deduped.append(paper)

    return deduped