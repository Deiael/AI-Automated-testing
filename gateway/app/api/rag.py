from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.config import settings
from app.persistence.db import get_db
from app.persistence.models import Project, RagDocument, RagEvalCase, RagKnowledgeBase
from app.rag import rag_service
from app.schemas.dto import RagDocOut, RagEvalCaseIn, RagEvalCaseOut, RagKbIn, RagKbOut

router = APIRouter(prefix="/api/projects/{project_id}/rag", tags=["rag"], dependencies=[Depends(require_api_key)])


class PreviewIn(BaseModel):
    content: str
    chunk_strategy: str = "fixed"
    chunk_size: int = 400
    chunk_overlap: int = 40


class SearchIn(BaseModel):
    query: str
    kb_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)


class EvalRunIn(BaseModel):
    kb_id: str
    top_k: int = Field(default=5, ge=1, le=50)


def _kb_out(kb: RagKnowledgeBase, db: Session) -> RagKbOut:
    doc_count = db.query(RagDocument).filter(RagDocument.kb_id == kb.id).count()
    return RagKbOut(
        id=kb.id,
        project_id=kb.project_id,
        name=kb.name,
        description=kb.description or "",
        chunk_strategy=kb.chunk_strategy,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        is_default=bool(kb.is_default),
        status=kb.status,
        doc_count=doc_count,
    )


@router.get("/meta")
def rag_meta():
    return {
        "strategies": rag_service.list_strategies(),
        "vector_store": settings.vector_store,
        "milvus_uri": settings.milvus_uri,
        "embedding_configured": bool(settings.embedding_base_url and settings.embedding_api_key),
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
        "top_k_default": settings.rag_top_k,
    }


@router.get("/knowledge-bases", response_model=list[RagKbOut])
def list_kbs(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    rag_service.ensure_default_kb(db, project_id)
    rows = (
        db.query(RagKnowledgeBase)
        .filter(RagKnowledgeBase.project_id == project_id)
        .order_by(RagKnowledgeBase.created_at.desc())
        .all()
    )
    return [_kb_out(r, db) for r in rows]


@router.post("/knowledge-bases", response_model=RagKbOut)
def create_kb(project_id: str, body: RagKbIn, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    kb = rag_service.create_kb(db, project_id, body.model_dump())
    return _kb_out(kb, db)


@router.put("/knowledge-bases/{kb_id}", response_model=RagKbOut)
def update_kb(project_id: str, kb_id: str, body: RagKbIn, db: Session = Depends(get_db)):
    try:
        kb = rag_service.update_kb(db, project_id, kb_id, body.model_dump(exclude_unset=True))
    except KeyError:
        raise HTTPException(404, "knowledge base not found") from None
    return _kb_out(kb, db)


@router.delete("/knowledge-bases/{kb_id}")
async def delete_kb(project_id: str, kb_id: str, db: Session = Depends(get_db)):
    await rag_service.delete_kb(db, project_id, kb_id)
    return {"ok": True}


@router.post("/preview")
def preview_chunks_api(project_id: str, body: PreviewIn, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    chunks = rag_service.preview(body.content, body.chunk_strategy, body.chunk_size, body.chunk_overlap)
    return {"count": len(chunks), "chunks": chunks}


@router.post("/search")
async def search_api(project_id: str, body: SearchIn, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    hits = await rag_service.search(project_id, body.query, top_k=body.top_k, kb_id=body.kb_id, db=db)
    return {
        "query": body.query,
        "top_k": body.top_k,
        "hits": [
            {
                "chunk_id": h.chunk_id,
                "doc_id": h.doc_id,
                "title": h.title,
                "text": h.text,
                "score": h.score,
                "section": h.section,
                "kb_id": h.kb_id,
            }
            for h in hits
        ],
    }


@router.get("/docs", response_model=list[RagDocOut])
def list_docs(project_id: str, kb_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(RagDocument).filter(RagDocument.project_id == project_id)
    if kb_id:
        q = q.filter(RagDocument.kb_id == kb_id)
    return q.order_by(RagDocument.created_at.desc()).all()


@router.get("/docs/{doc_id}")
def get_doc(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    row = db.get(RagDocument, doc_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "doc not found")
    return {
        "id": row.id,
        "project_id": row.project_id,
        "kb_id": row.kb_id,
        "title": row.title,
        "source": row.source,
        "status": row.status,
        "chunk_count": row.chunk_count,
        "chunk_strategy": row.chunk_strategy,
        "chunks": row.chunks_json or [],
        "content_preview": (row.content or "")[:2000],
    }


@router.post("/docs", response_model=RagDocOut)
async def upload_doc(
    project_id: str,
    title: str = Form(...),
    content: str = Form(""),
    kb_id: str = Form(""),
    chunk_strategy: str = Form(""),
    chunk_size: int = Form(0),
    chunk_overlap: int = Form(-1),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    source = ""
    if file is not None:
        raw = await file.read()
        content = raw.decode("utf-8", errors="ignore")
        source = file.filename or ""
        if not title:
            title = source or "untitled"
    if not content.strip():
        raise HTTPException(400, detail={"code": "GATEWAY_VALIDATION", "message": "empty content"})
    try:
        return await rag_service.index_document(
            db,
            project_id,
            title=title,
            content=content,
            source=source,
            kb_id=kb_id or None,
            strategy=chunk_strategy or None,
            chunk_size=chunk_size or None,
            chunk_overlap=None if chunk_overlap < 0 else chunk_overlap,
        )
    except KeyError:
        raise HTTPException(404, "knowledge base not found") from None
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, detail={"code": "RAG_INDEX_FAILED", "message": str(exc)}) from exc


@router.delete("/docs/{doc_id}")
async def delete_doc(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    await rag_service.delete_document(db, project_id, doc_id)
    return {"ok": True}


@router.post("/knowledge-bases/{kb_id}/reindex")
async def reindex_kb(project_id: str, kb_id: str, db: Session = Depends(get_db)):
    try:
        count = await rag_service.reindex_kb(db, project_id, kb_id)
    except KeyError:
        raise HTTPException(404, "knowledge base not found") from None
    return {"ok": True, "count": count}


@router.post("/reindex")
async def reindex(project_id: str, db: Session = Depends(get_db)):
    kb = rag_service.ensure_default_kb(db, project_id)
    count = await rag_service.reindex_kb(db, project_id, kb.id)
    return {"ok": True, "count": count}


@router.get("/eval-cases", response_model=list[RagEvalCaseOut])
def list_eval_cases(project_id: str, kb_id: str, db: Session = Depends(get_db)):
    return (
        db.query(RagEvalCase)
        .filter(RagEvalCase.project_id == project_id, RagEvalCase.kb_id == kb_id)
        .order_by(RagEvalCase.created_at.desc())
        .all()
    )


@router.post("/eval-cases", response_model=RagEvalCaseOut)
def create_eval_case(project_id: str, body: RagEvalCaseIn, db: Session = Depends(get_db)):
    kb = db.get(RagKnowledgeBase, body.kb_id)
    if not kb or kb.project_id != project_id:
        raise HTTPException(404, "knowledge base not found")
    row = RagEvalCase(
        project_id=project_id,
        kb_id=body.kb_id,
        query=body.query,
        expected_doc_ids=body.expected_doc_ids or [],
        expected_keywords=body.expected_keywords or [],
        note=body.note or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/eval-cases/{case_id}")
def delete_eval_case(project_id: str, case_id: str, db: Session = Depends(get_db)):
    row = db.get(RagEvalCase, case_id)
    if row and row.project_id == project_id:
        db.delete(row)
        db.commit()
    return {"ok": True}


@router.post("/eval/run")
async def run_eval(project_id: str, body: EvalRunIn, db: Session = Depends(get_db)):
    try:
        return await rag_service.evaluate(db, project_id, body.kb_id, top_k=body.top_k)
    except KeyError:
        raise HTTPException(404, "knowledge base not found") from None
