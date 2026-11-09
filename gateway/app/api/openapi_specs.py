from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_auth
from app.persistence.db import get_db
from app.persistence.models import ApiSpec, Project, TestCase, TestPoint
from app.services.openapi_import import build_point_and_cases, extract_operations, parse_openapi_text

router = APIRouter(tags=["openapi"], dependencies=[Depends(require_auth)])


class OpenApiImportUrlIn(BaseModel):
    project_id: str
    pipeline_id: Optional[str] = None
    url: str
    title: str = ""
    create_artifacts: bool = True
    confirm: bool = True


class OpenApiImportRawIn(BaseModel):
    project_id: str
    pipeline_id: Optional[str] = None
    content: str
    title: str = ""
    source: str = "paste"
    create_artifacts: bool = True
    confirm: bool = True


class SpecOut(BaseModel):
    id: str
    project_id: str
    pipeline_id: Optional[str] = None
    title: str
    version: str = ""
    source: str = ""
    operations_count: int = 0
    created_at: Any = None

    class Config:
        from_attributes = True


@router.get("/api/projects/{project_id}/api-specs")
def list_specs(project_id: str, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(ApiSpec).filter(ApiSpec.project_id == project_id)
    if pipeline_id:
        q = q.filter((ApiSpec.pipeline_id == pipeline_id) | (ApiSpec.pipeline_id.is_(None)))
    rows = q.order_by(ApiSpec.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "pipeline_id": r.pipeline_id,
            "title": r.title,
            "version": r.version,
            "source": r.source,
            "operations_count": len(r.operations_json or []),
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/api/api-specs/{spec_id}")
def get_spec(spec_id: str, db: Session = Depends(get_db)):
    row = db.get(ApiSpec, spec_id)
    if not row:
        raise HTTPException(404, "spec not found")
    return {
        "id": row.id,
        "project_id": row.project_id,
        "pipeline_id": row.pipeline_id,
        "title": row.title,
        "version": row.version,
        "source": row.source,
        "operations": row.operations_json or [],
        "created_at": row.created_at,
    }


@router.post("/api/openapi/import")
async def import_openapi(
    project_id: str = Form(...),
    pipeline_id: str | None = Form(default=None),
    title: str = Form(default=""),
    create_artifacts: bool = Form(default=True),
    confirm: bool = Form(default=True),
    url: str | None = Form(default=None),
    content: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    pipeline_id = (pipeline_id or "").strip() or None
    raw = ""
    source = "paste"
    file_bytes = b""
    if file is not None:
        file_bytes = await file.read()
    if file_bytes:
        raw = file_bytes.decode("utf-8", errors="ignore")
        source = file.filename or "upload"
    elif content:
        raw = content
        source = "paste"
    elif url:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                raw = resp.text
            source = url
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"failed to fetch url: {exc}") from exc
    else:
        raise HTTPException(400, "provide file, content, or url")

    return _do_import(
        db,
        project_id=project_id,
        pipeline_id=pipeline_id or None,
        raw=raw,
        source=source,
        title=title,
        create_artifacts=create_artifacts,
        confirm=confirm,
    )


@router.post("/api/openapi/import/json")
def import_openapi_json(body: OpenApiImportRawIn, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    return _do_import(
        db,
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        raw=body.content,
        source=body.source or "paste",
        title=body.title,
        create_artifacts=body.create_artifacts,
        confirm=body.confirm,
    )


@router.post("/api/openapi/import/url")
def import_openapi_url(body: OpenApiImportUrlIn, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(body.url)
            resp.raise_for_status()
            raw = resp.text
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"failed to fetch url: {exc}") from exc
    return _do_import(
        db,
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        raw=raw,
        source=body.url,
        title=body.title,
        create_artifacts=body.create_artifacts,
        confirm=body.confirm,
    )


@router.delete("/api/api-specs/{spec_id}")
def delete_spec(spec_id: str, db: Session = Depends(get_db)):
    row = db.get(ApiSpec, spec_id)
    if not row:
        raise HTTPException(404, "spec not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


def _do_import(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None,
    raw: str,
    source: str,
    title: str,
    create_artifacts: bool,
    confirm: bool,
) -> dict[str, Any]:
    try:
        spec = parse_openapi_text(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"invalid OpenAPI: {exc}") from exc
    ops = extract_operations(spec)
    info = spec.get("info") if isinstance(spec.get("info"), dict) else {}
    row = ApiSpec(
        project_id=project_id,
        pipeline_id=pipeline_id,
        title=(title or info.get("title") or "OpenAPI"),
        version=str(info.get("version") or ""),
        source=source,
        raw_json=spec,
        operations_json=ops,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    points_created = 0
    cases_created = 0
    if create_artifacts:
        for op in ops:
            point_data, cases_data = build_point_and_cases(
                op, project_id=project_id, pipeline_id=pipeline_id, confirm=confirm
            )
            point = TestPoint(**point_data)
            db.add(point)
            db.flush()
            points_created += 1
            for cd in cases_data:
                db.add(
                    TestCase(
                        project_id=project_id,
                        pipeline_id=pipeline_id,
                        test_point_id=point.id,
                        title=cd["title"],
                        content_json=cd["content_json"],
                        status=cd["status"],
                        confidence=0.85,
                    )
                )
                cases_created += 1
        db.commit()

    return {
        "spec_id": row.id,
        "title": row.title,
        "version": row.version,
        "operations": len(ops),
        "points_created": points_created,
        "cases_created": cases_created,
        "operations_preview": ops[:20],
    }
