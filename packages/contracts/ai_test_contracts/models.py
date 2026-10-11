from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class FlowType(str, Enum):
    TEST_POINT = "TEST_POINT"
    TEST_CASE = "TEST_CASE"
    TEST_EXECUTE = "TEST_EXECUTE"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ContextChunk(BaseModel):
    doc_id: str
    title: str = ""
    text: str
    score: float = 0.0


class TemplateSpec(BaseModel):
    name: str = "api-case-v1"
    # avoid BaseModel.schema shadowing; wire JSON key remains schema_json
    fields_schema: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="schema_json",
        serialization_alias="schema_json",
    )
    prompt_hint: str = ""

    model_config = {"populate_by_name": True}


class RuntimeConfig(BaseModel):
    base_url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)


class EngineRequest(BaseModel):
    request_id: str
    flow: FlowType
    model: str = "gpt-4o-mini"
    session_id: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
    context_chunks: list[ContextChunk] = Field(default_factory=list)
    template: Optional[TemplateSpec] = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    options: dict[str, Any] = Field(default_factory=lambda: {"temperature": 0.2, "locale": "zh-CN"})


class EngineEvent(BaseModel):
    event: Literal[
        "meta",
        "token",
        "message",
        "artifact",
        "progress",
        "ask_user",
        "error",
        "done",
    ]
    data: dict[str, Any] = Field(default_factory=dict)
