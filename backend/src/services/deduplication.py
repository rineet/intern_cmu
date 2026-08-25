from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas import PaperSummary


def clean_doi(doi: str | None) -> str | None:
    """Safely cleans and normalizes DOIs."""
    if not doi:
        return None
    cleaned = str(doi).strip().lower()
    # Remove common prefix artifacts if present
    cleaned = re.sub(r"^https?://(dx\.)?doi\.org/", "", cleaned)
    return cleaned if cleaned else None


def normalize_title_fingerprint(title: str | None) -> str:
    """
    Creates an exact title fingerprint by converting to lowercase,
    removing all non-alphanumeric characters, and collapsing whitespace.
    
    Example:
      "Attention Is All You Need!" -> "attentionisallyouneed"
    """
    if not title:
        return ""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def deduplicate_papers(papers: list[PaperSummary]) -> list[PaperSummary]:
    """
    Blazingly fast O(N) deduplication using Hash Sets for DOIs and Title Fingerprints.
    Processes 10,000+ papers in milliseconds.
    """
    seen_dois: set[str] = set()
    seen_fingerprints: set[str] = set()
    deduped: list[PaperSummary] = []

    for paper in papers:
        doi = clean_doi(paper.doi)
        fingerprint = normalize_title_fingerprint(paper.title)

        # 1. Deduplicate by DOI (Primary Key)
        if doi and doi in seen_dois:
            continue

        # 2. Deduplicate by Title Fingerprint (Secondary Key)
        if fingerprint and fingerprint in seen_fingerprints:
            continue

        # Record identifiers if kept
        if doi:
            seen_dois.add(doi)
        if fingerprint:
            seen_fingerprints.add(fingerprint)

        deduped.append(paper)

    return deduped