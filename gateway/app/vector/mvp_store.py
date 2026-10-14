from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from app.vector.base import Chunk, ScoredChunk

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    parts = _TOKEN_RE.findall(text.lower())
    tokens: list[str] = []
    for p in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", p) and len(p) > 1:
            tokens.extend(list(p))
            tokens.append(p)
        else:
            tokens.append(p)
    return tokens


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class MvpVectorStore:
    """File-backed bag-of-words store keyed by knowledge-base id."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, collection_key: str) -> Path:
        safe = collection_key.replace("/", "_").replace("\\", "_")
        return self.root / f"{safe}.json"

    def _load(self, collection_key: str) -> list[dict]:
        p = self._path(collection_key)
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, collection_key: str, rows: list[dict]) -> None:
        self._path(collection_key).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    async def upsert(self, collection_key: str, chunks: list[Chunk]) -> None:
        rows = self._load(collection_key)
        doc_ids = {c.doc_id for c in chunks}
        rows = [r for r in rows if r["doc_id"] not in doc_ids]
        for c in chunks:
            rows.append(
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "text": c.text,
                    "section": c.section,
                    "kb_id": collection_key,
                    "tf": dict(Counter(_tokenize(c.text))),
                }
            )
        self._save(collection_key, rows)

    async def delete(self, collection_key: str, doc_id: str) -> None:
        rows = [r for r in self._load(collection_key) if r["doc_id"] != doc_id]
        self._save(collection_key, rows)

    async def search(self, collection_key: str, query: str, top_k: int) -> list[ScoredChunk]:
        q = Counter(_tokenize(query))
        if not q:
            return []
        scored: list[ScoredChunk] = []
        for r in self._load(collection_key):
            tf = r.get("tf") or {}
            score = _cosine(q, Counter(tf))
            if score <= 0:
                continue
            scored.append(
                ScoredChunk(
                    chunk_id=r["chunk_id"],
                    doc_id=r["doc_id"],
                    title=r.get("title") or "",
                    text=r.get("text") or "",
                    score=score,
                    section=r.get("section") or "",
                    kb_id=r.get("kb_id") or collection_key,
                )
            )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    async def drop(self, collection_key: str) -> None:
        p = self._path(collection_key)
        if p.exists():
            p.unlink()

    # backward alias
    async def drop_project(self, project_id: str) -> None:
        await self.drop(project_id)
