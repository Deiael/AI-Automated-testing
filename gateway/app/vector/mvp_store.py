from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from app.vector.base import Chunk, ScoredChunk


class MvpVectorStore:
    """File-backed bag-of-words store. Replaceable by MilvusVectorStore later."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self.root / f"{project_id}.json"

    def _load(self, project_id: str) -> list[dict]:
        p = self._path(project_id)
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, project_id: str, rows: list[dict]) -> None:
        self._path(project_id).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    async def upsert(self, project_id: str, chunks: list[Chunk]) -> None:
        rows = self._load(project_id)
        doc_ids = {c.doc_id for c in chunks}
        rows = [r for r in rows if r["doc_id"] not in doc_ids]
        for c in chunks:
            rows.append(
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "text": c.text,
                    "tf": dict(Counter(_tokenize(c.text))),
                }
            )
        self._save(project_id, rows)

    async def delete(self, project_id: str, doc_id: str) -> None:
        rows = [r for r in self._load(project_id) if r["doc_id"] != doc_id]
        self._save(project_id, rows)

    async def search(self, project_id: str, query: str, top_k: int) -> list[ScoredChunk]:
        q = Counter(_tokenize(query))
        if not q:
            return []
        scored: list[ScoredChunk] = []
        for r in self._load(project_id):
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
                )
            )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    async def drop_project(self, project_id: str) -> None:
        p = self._path(project_id)
        if p.exists():
            p.unlink()


class MilvusVectorStore:
    """Placeholder for future Milvus integration."""

    def __init__(self, *_args, **_kwargs) -> None:
        raise NotImplementedError("MilvusVectorStore is reserved. Set VECTOR_STORE=mvp for now.")


def get_vector_store(kind: str, root: str) -> MvpVectorStore:
    if kind == "milvus":
        return MilvusVectorStore()  # type: ignore[return-value]
    return MvpVectorStore(root)


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
