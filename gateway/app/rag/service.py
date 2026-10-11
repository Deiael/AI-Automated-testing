from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.persistence.models import RagDocument
from app.vector import Chunk, get_vector_store


def chunk_text(text: str, size: int = 400, overlap: int = 40) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return chunks


class RagService:
    def __init__(self) -> None:
        self.store = get_vector_store(settings.vector_store, settings.vector_data_dir)

    async def index_document(self, db: Session, project_id: str, title: str, content: str, source: str = "") -> RagDocument:
        doc = RagDocument(project_id=project_id, title=title, content=content, source=source, status="indexing")
        db.add(doc)
        db.commit()
        db.refresh(doc)

        parts = chunk_text(content)
        chunks = [
            Chunk(chunk_id=str(uuid.uuid4()), doc_id=doc.id, title=title, text=part)
            for part in parts
        ]
        try:
            await self.store.upsert(project_id, chunks)
            doc.chunk_count = len(chunks)
            doc.status = "indexed"
        except Exception:
            doc.status = "failed"
            db.commit()
            raise
        db.commit()
        db.refresh(doc)
        return doc

    async def delete_document(self, db: Session, project_id: str, doc_id: str) -> None:
        await self.store.delete(project_id, doc_id)
        row = db.get(RagDocument, doc_id)
        if row and row.project_id == project_id:
            db.delete(row)
            db.commit()

    async def search(self, project_id: str, query: str, top_k: int | None = None):
        return await self.store.search(project_id, query, top_k or settings.rag_top_k)


rag_service = RagService()
