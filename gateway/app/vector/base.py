from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str


@dataclass
class ScoredChunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    score: float


class VectorStore(Protocol):
    async def upsert(self, project_id: str, chunks: list[Chunk]) -> None: ...

    async def delete(self, project_id: str, doc_id: str) -> None: ...

    async def search(self, project_id: str, query: str, top_k: int) -> list[ScoredChunk]: ...

    async def drop_project(self, project_id: str) -> None: ...
