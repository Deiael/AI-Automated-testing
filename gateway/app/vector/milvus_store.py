from __future__ import annotations

import logging
import re
from typing import Any

from app.config import settings
from app.rag.embedding import embed_query, embed_texts
from app.vector.base import Chunk, ScoredChunk

logger = logging.getLogger(__name__)

COLLECTION = "ai_test_rag_chunks"


class MilvusVectorStore:
    """Milvus / Milvus Lite store with dense embeddings + kb_id filter."""

    def __init__(self, uri: str | None = None) -> None:
        try:
            from pymilvus import DataType, MilvusClient
        except ImportError as e:
            raise RuntimeError('pymilvus not installed. Run: pip install "pymilvus>=2.4"') from e

        self.uri = uri or settings.milvus_uri
        self.dim = settings.embedding_dim
        self.client = MilvusClient(uri=self.uri)
        self._DataType = DataType
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.has_collection(COLLECTION):
            return
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="chunk_id", datatype=self._DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field(field_name="kb_id", datatype=self._DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="doc_id", datatype=self._DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="title", datatype=self._DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="section", datatype=self._DataType.VARCHAR, max_length=256)
        schema.add_field(field_name="text", datatype=self._DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="vector", datatype=self._DataType.FLOAT_VECTOR, dim=self.dim)
        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
        self.client.create_collection(collection_name=COLLECTION, schema=schema, index_params=index_params)
        logger.info("created milvus collection %s dim=%s uri=%s", COLLECTION, self.dim, self.uri)

    def _escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    async def upsert(self, collection_key: str, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        doc_ids = {c.doc_id for c in chunks}
        for doc_id in doc_ids:
            await self.delete(collection_key, doc_id)
        vectors = embed_texts([c.text for c in chunks])
        rows: list[dict[str, Any]] = []
        for c, vec in zip(chunks, vectors):
            rows.append(
                {
                    "chunk_id": c.chunk_id,
                    "kb_id": collection_key,
                    "doc_id": c.doc_id,
                    "title": (c.title or "")[:500],
                    "section": (c.section or "")[:250],
                    "text": (c.text or "")[:65000],
                    "vector": vec,
                }
            )
        self.client.insert(collection_name=COLLECTION, data=rows)

    async def delete(self, collection_key: str, doc_id: str) -> None:
        expr = f'kb_id == "{self._escape(collection_key)}" and doc_id == "{self._escape(doc_id)}"'
        try:
            self.client.delete(collection_name=COLLECTION, filter=expr)
        except Exception:
            logger.exception("milvus delete failed kb=%s doc=%s", collection_key, doc_id)

    async def search(self, collection_key: str, query: str, top_k: int) -> list[ScoredChunk]:
        if not (query or "").strip():
            return []
        vec = embed_query(query)
        filt = f'kb_id == "{self._escape(collection_key)}"'
        raw = self.client.search(
            collection_name=COLLECTION,
            data=[vec],
            filter=filt,
            limit=top_k,
            output_fields=["chunk_id", "doc_id", "title", "text", "section", "kb_id"],
        )
        hits = raw[0] if raw else []
        out: list[ScoredChunk] = []
        for h in hits:
            entity = h.get("entity") or h
            out.append(
                ScoredChunk(
                    chunk_id=str(entity.get("chunk_id") or h.get("id") or ""),
                    doc_id=str(entity.get("doc_id") or ""),
                    title=str(entity.get("title") or ""),
                    text=str(entity.get("text") or ""),
                    score=float(h.get("distance") if h.get("distance") is not None else h.get("score") or 0.0),
                    section=str(entity.get("section") or ""),
                    kb_id=str(entity.get("kb_id") or collection_key),
                )
            )
        return out

    async def drop(self, collection_key: str) -> None:
        expr = f'kb_id == "{self._escape(collection_key)}"'
        try:
            self.client.delete(collection_name=COLLECTION, filter=expr)
        except Exception:
            logger.exception("milvus drop failed kb=%s", collection_key)
