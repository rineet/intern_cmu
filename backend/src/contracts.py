from __future__ import annotations

from typing import Protocol


class PdfRetrievalContract(Protocol):
    async def get_pdf(self, paper_id: str) -> bytes:  # pragma: no cover - placeholder contract
        raise NotImplementedError


class RagIndexingContract(Protocol):
    async def index(self, paper_id: str) -> None:  # pragma: no cover - placeholder contract
        raise NotImplementedError


class BibliographyGenerationContract(Protocol):
    async def generate(self, paper_ids: list[str]) -> str:  # pragma: no cover - placeholder contract
        raise NotImplementedError