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
    kb_id: Optional[str] = None
    title: str
    source: str
    status: str
    chunk_count: int
    chunk_strategy: str = ""

    class Config:
        from_attributes = True


class RagKbIn(BaseModel):
    name: str = "未命名知识库"
    description: str = ""
    chunk_strategy: str = "fixed"
    chunk_size: int = 400
    chunk_overlap: int = 40
    is_default: bool = False
    status: Optional[str] = None


class RagKbOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: str = ""
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    is_default: bool = False
    status: str = "active"
    doc_count: int = 0

    class Config:
        from_attributes = True


class RagEvalCaseIn(BaseModel):
    kb_id: str
    query: str
    expected_doc_ids: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    note: str = ""


class RagEvalCaseOut(BaseModel):
    id: str
    project_id: str
    kb_id: str
    query: str
    expected_doc_ids: list = Field(default_factory=list)
    expected_keywords: list = Field(default_factory=list)
    note: str = ""

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


class SkillIn(BaseModel):
    name: str
    description: str = ""
    content: str = ""
    enabled: bool = True


class SkillOut(SkillIn):
    id: str
    project_id: str

    class Config:
        from_attributes = True


class McpServerIn(BaseModel):
    name: str
    transport: str = "http"  # sse | http | stdio
    url: str = ""
    command: str = ""
    args_json: list[Any] = Field(default_factory=list)
    headers_json: dict[str, str] = Field(default_factory=dict)
    env_json: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class McpServerOut(McpServerIn):
    id: str
    project_id: str
    tools_cache_json: list[Any] = Field(default_factory=list)
    last_sync_at: Optional[str] = None
    last_error: str = ""

    class Config:
        from_attributes = True


class McpCallIn(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
