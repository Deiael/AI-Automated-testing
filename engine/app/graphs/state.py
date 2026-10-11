from __future__ import annotations

from typing import Any, TypedDict

from ai_test_contracts import EngineRequest


class GraphState(TypedDict, total=False):
    request: dict[str, Any]
    analysis: str
    drafts: list[dict[str, Any]]
    message: str
    need_user: bool
    questions: list[str]
    report: dict[str, Any]
    progress: list[dict[str, Any]]


def req_from_state(state: GraphState) -> EngineRequest:
    return EngineRequest.model_validate(state["request"])
