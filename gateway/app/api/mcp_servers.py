from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.mcp_client import McpError, call_tool, list_tools
from app.persistence.db import get_db
from app.persistence.models import Project, ProjectMcpServer
from app.schemas.dto import McpCallIn, McpServerIn, McpServerOut

router = APIRouter(prefix="/api/projects", tags=["mcp"], dependencies=[Depends(require_api_key)])


def _out(row: ProjectMcpServer) -> McpServerOut:
    return McpServerOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        transport=row.transport,
        url=row.url or "",
        command=row.command or "",
        args_json=row.args_json or [],
        headers_json=row.headers_json or {},
        env_json=row.env_json or {},
        enabled=bool(row.enabled),
        tools_cache_json=row.tools_cache_json or [],
        last_sync_at=row.last_sync_at.isoformat() if row.last_sync_at else None,
        last_error=row.last_error or "",
    )


@router.get("/{project_id}/mcp-servers", response_model=list[McpServerOut])
def list_mcp_servers(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    rows = (
        db.query(ProjectMcpServer)
        .filter(ProjectMcpServer.project_id == project_id)
        .order_by(ProjectMcpServer.created_at.desc())
        .all()
    )
    return [_out(r) for r in rows]


@router.post("/{project_id}/mcp-servers", response_model=McpServerOut)
def create_mcp_server(project_id: str, body: McpServerIn, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    transport = (body.transport or "http").lower()
    if transport not in {"http", "sse", "stdio"}:
        raise HTTPException(400, "transport must be http|sse|stdio")
    row = ProjectMcpServer(project_id=project_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.put("/{project_id}/mcp-servers/{server_id}", response_model=McpServerOut)
def update_mcp_server(project_id: str, server_id: str, body: McpServerIn, db: Session = Depends(get_db)):
    row = db.get(ProjectMcpServer, server_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "mcp server not found")
    transport = (body.transport or "http").lower()
    if transport not in {"http", "sse", "stdio"}:
        raise HTTPException(400, "transport must be http|sse|stdio")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/{project_id}/mcp-servers/{server_id}")
def delete_mcp_server(project_id: str, server_id: str, db: Session = Depends(get_db)):
    row = db.get(ProjectMcpServer, server_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "mcp server not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/{project_id}/mcp-servers/{server_id}/probe", response_model=McpServerOut)
async def probe_mcp_server(project_id: str, server_id: str, db: Session = Depends(get_db)):
    row = db.get(ProjectMcpServer, server_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "mcp server not found")
    try:
        tools = await list_tools(transport=row.transport, url=row.url or "", headers=row.headers_json or {})
        row.tools_cache_json = tools
        row.last_sync_at = datetime.utcnow()
        row.last_error = ""
    except McpError as exc:
        row.last_error = str(exc)
        db.commit()
        db.refresh(row)
        raise HTTPException(status_code=400, detail={"code": "MCP_PROBE_FAILED", "message": str(exc)}) from exc
    db.commit()
    db.refresh(row)
    return _out(row)


@router.post("/{project_id}/mcp-servers/{server_id}/call")
async def call_mcp_tool(project_id: str, server_id: str, body: McpCallIn, db: Session = Depends(get_db)):
    row = db.get(ProjectMcpServer, server_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "mcp server not found")
    try:
        result = await call_tool(
            transport=row.transport,
            url=row.url or "",
            tool_name=body.tool_name,
            arguments=body.arguments,
            headers=row.headers_json or {},
        )
        return {"ok": True, "result": result}
    except McpError as exc:
        raise HTTPException(status_code=400, detail={"code": "MCP_CALL_FAILED", "message": str(exc)}) from exc
