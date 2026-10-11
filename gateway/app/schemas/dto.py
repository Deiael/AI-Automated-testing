from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class EngineProfileIn(BaseModel):
    name: str
    engine_base_url: str
    model: str = "gpt-4o-mini"
    vendor: str = "langgraph"
    extra_json: dict[str, Any] = Field(default_factory=dict)


class EngineProfileOut(EngineProfileIn):
    id: str

    class Config:
        from_attributes = True


class ProjectIn(BaseModel):
    name: str
    description: str = ""
    engine_profile_id: Optional[str] = None
    runtime_base_url: str = ""
    runtime_headers: dict[str, str] = Field(default_factory=dict)


class ProjectOut(ProjectIn):
    id: str
    status: str

    class Config:
        from_attributes = True


class TemplateIn(BaseModel):
    name: str
    schema_json: dict[str, Any] = Field(default_factory=dict)
    prompt_hint: str = ""


class TemplateOut(TemplateIn):
    id: str
    project_id: str

    class Config:
        from_attributes = True


class RagDocOut(BaseModel):
    id: str
    project_id: str
    title: str
    source: str
    status: str
    chunk_count: int

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    project_id: str
    flow_type: str
    title: str = ""
    template_id: Optional[str] = None
    engine_profile_id: Optional[str] = None


class SessionOut(BaseModel):
    id: str
    project_id: str
    flow_type: str
    status: str
    title: str
    template_id: Optional[str] = None
    engine_profile_id: Optional[str] = None

    class Config:
        from_attributes = True


class ChatIn(BaseModel):
    message: str
    engine_profile_id: Optional[str] = None
    test_point_ids: list[str] = Field(default_factory=list)
    test_case_ids: list[str] = Field(default_factory=list)


class MessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    event_type: str

    class Config:
        from_attributes = True


class ArtifactPatch(BaseModel):
    title: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    status: Optional[str] = None


class TestRunCreate(BaseModel):
    project_id: str
    case_ids: list[str]
    engine_profile_id: Optional[str] = None
