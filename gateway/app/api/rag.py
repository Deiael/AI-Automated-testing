from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.persistence.db import get_db
from app.persistence.models import Project, RagDocument
from app.rag import rag_service
from app.schemas.dto import RagDocOut

router = APIRouter(prefix="/api/projects/{project_id}/rag", tags=["rag"], dependencies=[Depends(require_api_key)])


@router.get("/docs", response_model=list[RagDocOut])
def list_docs(project_id: str, db: Session = Depends(get_db)):
    return db.query(RagDocument).filter(RagDocument.project_id == project_id).order_by(RagDocument.created_at.desc()).all()


@router.post("/docs", response_model=RagDocOut)
async def upload_doc(
    project_id: str,
    title: str = Form(...),
    content: str = Form(""),
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
        return await rag_service.index_document(db, project_id, title=title, content=content, source=source)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, detail={"code": "RAG_INDEX_FAILED", "message": str(exc)}) from exc


@router.delete("/docs/{doc_id}")
async def delete_doc(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    await rag_service.delete_document(db, project_id, doc_id)
    return {"ok": True}


@router.post("/reindex")
async def reindex(project_id: str, db: Session = Depends(get_db)):
    import uuid

    from app.rag.service import chunk_text
    from app.vector import Chunk

    docs = db.query(RagDocument).filter(RagDocument.project_id == project_id).all()
    for d in docs:
        await rag_service.store.delete(project_id, d.id)
        parts = chunk_text(d.content or "")
        chunks = [
            Chunk(chunk_id=str(uuid.uuid4()), doc_id=d.id, title=d.title, text=part) for part in parts
        ]
        await rag_service.store.upsert(project_id, chunks)
        d.chunk_count = len(chunks)
        d.status = "indexed"
    db.commit()
    return {"ok": True, "count": len(docs)}
