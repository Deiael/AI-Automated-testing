from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    section: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ScoredChunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    score: float
    section: str = ""
    kb_id: str = ""


class VectorStore(Protocol):
    """collection_key is typically knowledge-base id."""

    async def upsert(self, collection_key: str, chunks: list[Chunk]) -> None: ...

    async def delete(self, collection_key: str, doc_id: str) -> None: ...

    async def search(self, collection_key: str, query: str, top_k: int) -> list[ScoredChunk]: ...

    async def drop(self, collection_key: str) -> None: ...
