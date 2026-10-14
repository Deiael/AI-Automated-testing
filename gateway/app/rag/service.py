from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.persistence.models import RagDocument, RagEvalCase, RagKnowledgeBase
from app.rag.chunking import STRATEGIES, preview_chunks
from app.vector import Chunk, get_vector_store


class RagService:
    def __init__(self) -> None:
        self.store = get_vector_store()

    def list_strategies(self) -> list[dict]:
        return STRATEGIES

    def ensure_default_kb(self, db: Session, project_id: str) -> RagKnowledgeBase:
        row = (
            db.query(RagKnowledgeBase)
            .filter(RagKnowledgeBase.project_id == project_id, RagKnowledgeBase.is_default.is_(True))
            .first()
        )
        if row:
            return row
        any_kb = db.query(RagKnowledgeBase).filter(RagKnowledgeBase.project_id == project_id).first()
        if any_kb:
            any_kb.is_default = True
            db.commit()
            db.refresh(any_kb)
            return any_kb
        kb = RagKnowledgeBase(
            project_id=project_id,
            name="默认知识库",
            description="项目默认 RAG 知识库",
            chunk_strategy="fixed",
            chunk_size=400,
            chunk_overlap=40,
            is_default=True,
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)
        # migrate legacy docs without kb_id
        legacy = db.query(RagDocument).filter(RagDocument.project_id == project_id, RagDocument.kb_id.is_(None)).all()
        for d in legacy:
            d.kb_id = kb.id
        if legacy:
            db.commit()
        return kb

    def create_kb(self, db: Session, project_id: str, data: dict[str, Any]) -> RagKnowledgeBase:
        existing = db.query(RagKnowledgeBase).filter(RagKnowledgeBase.project_id == project_id).count()
        kb = RagKnowledgeBase(
            project_id=project_id,
            name=data.get("name") or "未命名知识库",
            description=data.get("description") or "",
            chunk_strategy=data.get("chunk_strategy") or "fixed",
            chunk_size=int(data.get("chunk_size") or 400),
            chunk_overlap=int(data.get("chunk_overlap") or 40),
            is_default=bool(data.get("is_default")) or existing == 0,
        )
        if kb.is_default:
            for row in db.query(RagKnowledgeBase).filter(RagKnowledgeBase.project_id == project_id).all():
                row.is_default = False
        db.add(kb)
        db.commit()
        db.refresh(kb)
        return kb

    def update_kb(self, db: Session, project_id: str, kb_id: str, data: dict[str, Any]) -> RagKnowledgeBase:
        kb = db.get(RagKnowledgeBase, kb_id)
        if not kb or kb.project_id != project_id:
            raise KeyError("kb not found")
        for key in ("name", "description", "chunk_strategy", "status"):
            if key in data and data[key] is not None:
                setattr(kb, key, data[key])
        if "chunk_size" in data and data["chunk_size"] is not None:
            kb.chunk_size = int(data["chunk_size"])
        if "chunk_overlap" in data and data["chunk_overlap"] is not None:
            kb.chunk_overlap = int(data["chunk_overlap"])
        if data.get("is_default"):
            for row in db.query(RagKnowledgeBase).filter(RagKnowledgeBase.project_id == project_id).all():
                row.is_default = row.id == kb_id
            kb.is_default = True
        db.commit()
        db.refresh(kb)
        return kb

    async def delete_kb(self, db: Session, project_id: str, kb_id: str) -> None:
        kb = db.get(RagKnowledgeBase, kb_id)
        if not kb or kb.project_id != project_id:
            return
        docs = db.query(RagDocument).filter(RagDocument.kb_id == kb_id).all()
        for d in docs:
            await self.store.delete(kb_id, d.id)
            db.delete(d)
        await self.store.drop(kb_id)
        db.query(RagEvalCase).filter(RagEvalCase.kb_id == kb_id).delete()
        db.delete(kb)
        db.commit()

    def preview(
        self,
        content: str,
        strategy: str = "fixed",
        size: int = 400,
        overlap: int = 40,
    ) -> list[dict]:
        return [c.to_dict() for c in preview_chunks(content, strategy=strategy, size=size, overlap=overlap)]

    async def index_document(
        self,
        db: Session,
        project_id: str,
        title: str,
        content: str,
        source: str = "",
        kb_id: str | None = None,
        strategy: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> RagDocument:
        kb = None
        if kb_id:
            kb = db.get(RagKnowledgeBase, kb_id)
            if not kb or kb.project_id != project_id:
                raise KeyError("kb not found")
        else:
            kb = self.ensure_default_kb(db, project_id)

        strat = strategy or kb.chunk_strategy or "fixed"
        size = chunk_size if chunk_size is not None else kb.chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else kb.chunk_overlap

        doc = RagDocument(
            project_id=project_id,
            kb_id=kb.id,
            title=title,
            content=content,
            source=source,
            chunk_strategy=strat,
            status="indexing",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        previews = preview_chunks(content, strategy=strat, size=size, overlap=overlap)
        chunks = [
            Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc.id,
                title=title,
                text=p.text,
                section=p.section,
            )
            for p in previews
        ]
        try:
            await self.store.upsert(kb.id, chunks)
            doc.chunk_count = len(chunks)
            doc.chunks_json = [p.to_dict() for p in previews]
            doc.status = "indexed"
        except Exception:
            doc.status = "failed"
            db.commit()
            raise
        db.commit()
        db.refresh(doc)
        return doc

    async def delete_document(self, db: Session, project_id: str, doc_id: str) -> None:
        row = db.get(RagDocument, doc_id)
        if not row or row.project_id != project_id:
            return
        key = row.kb_id or project_id
        await self.store.delete(key, doc_id)
        db.delete(row)
        db.commit()

    async def search(
        self,
        project_id: str,
        query: str,
        top_k: int | None = None,
        kb_id: str | None = None,
        db: Session | None = None,
    ):
        k = top_k or settings.rag_top_k
        if kb_id:
            hits = await self.store.search(kb_id, query, k)
            for h in hits:
                h.kb_id = kb_id
            return hits
        if db is None:
            # legacy: search using project_id key (old mvp files)
            return await self.store.search(project_id, query, k)

        kbs = db.query(RagKnowledgeBase).filter(RagKnowledgeBase.project_id == project_id).all()
        if not kbs:
            return await self.store.search(project_id, query, k)
        merged = []
        for kb in kbs:
            merged.extend(await self.store.search(kb.id, query, k))
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:k]

    async def reindex_kb(self, db: Session, project_id: str, kb_id: str) -> int:
        kb = db.get(RagKnowledgeBase, kb_id)
        if not kb or kb.project_id != project_id:
            raise KeyError("kb not found")
        docs = db.query(RagDocument).filter(RagDocument.kb_id == kb_id).all()
        for d in docs:
            await self.store.delete(kb_id, d.id)
            previews = preview_chunks(
                d.content or "",
                strategy=d.chunk_strategy or kb.chunk_strategy,
                size=kb.chunk_size,
                overlap=kb.chunk_overlap,
            )
            chunks = [
                Chunk(chunk_id=str(uuid.uuid4()), doc_id=d.id, title=d.title, text=p.text, section=p.section)
                for p in previews
            ]
            await self.store.upsert(kb_id, chunks)
            d.chunk_count = len(chunks)
            d.chunks_json = [p.to_dict() for p in previews]
            d.status = "indexed"
        db.commit()
        return len(docs)

    async def evaluate(
        self,
        db: Session,
        project_id: str,
        kb_id: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        kb = db.get(RagKnowledgeBase, kb_id)
        if not kb or kb.project_id != project_id:
            raise KeyError("kb not found")
        cases = db.query(RagEvalCase).filter(RagEvalCase.kb_id == kb_id).all()
        if not cases:
            return {"total": 0, "hit_at_k": 0.0, "keyword_recall": 0.0, "cases": []}

        details = []
        hits = 0
        kw_scores: list[float] = []
        for case in cases:
            retrieved = await self.store.search(kb_id, case.query, top_k)
            doc_ids = {r.doc_id for r in retrieved}
            expected_docs = set(case.expected_doc_ids or [])
            doc_hit = bool(expected_docs & doc_ids) if expected_docs else False

            keywords = [str(x).lower() for x in (case.expected_keywords or []) if str(x).strip()]
            blob = "\n".join(r.text for r in retrieved).lower()
            if keywords:
                found = sum(1 for kw in keywords if kw.lower() in blob)
                kw_recall = found / len(keywords)
            else:
                kw_recall = 1.0 if doc_hit or not expected_docs else 0.0

            ok = doc_hit or (keywords and kw_recall > 0)
            if ok:
                hits += 1
            kw_scores.append(kw_recall)
            details.append(
                {
                    "id": case.id,
                    "query": case.query,
                    "hit": ok,
                    "doc_hit": doc_hit,
                    "keyword_recall": round(kw_recall, 4),
                    "retrieved": [
                        {
                            "doc_id": r.doc_id,
                            "title": r.title,
                            "score": round(r.score, 4),
                            "preview": (r.text or "")[:160],
                        }
                        for r in retrieved
                    ],
                }
            )

        n = len(cases)
        return {
            "total": n,
            "top_k": top_k,
            "hit_at_k": round(hits / n, 4),
            "keyword_recall": round(sum(kw_scores) / n, 4),
            "vector_store": settings.vector_store,
            "cases": details,
        }


rag_service = RagService()
