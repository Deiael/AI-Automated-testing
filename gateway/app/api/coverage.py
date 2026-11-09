from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_auth
from app.persistence.db import get_db
from app.persistence.models import Project
from app.services.coverage import coverage_board

router = APIRouter(prefix="/api/coverage", tags=["coverage"], dependencies=[Depends(require_auth)])


@router.get("")
def get_coverage(
    project_id: str,
    pipeline_id: str | None = None,
    spec_id: str | None = None,
    db: Session = Depends(get_db),
):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    return coverage_board(db, project_id=project_id, pipeline_id=pipeline_id, spec_id=spec_id)
