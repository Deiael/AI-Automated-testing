from __future__ import annotations

from typing import Any

from ai_test_contracts import EngineRequest


def mock_test_points(req: EngineRequest) -> dict[str, Any]:
    user = _last_user(req)
    ctx = "；".join(c.title or c.text[:40] for c in req.context_chunks[:3])
    base = user[:80] or "未命名接口"
    points = [
        {
            "title": f"正常路径校验：{base}",
            "description": f"验证主流程成功响应。上下文参考：{ctx or '无'}",
            "priority": "P0",
            "module": "接口功能",
        },
        {
            "title": f"参数校验：{base}",
            "description": "非法/缺失参数时应返回 4xx 并带错误信息",
            "priority": "P1",
            "module": "参数校验",
        },
        {
            "title": f"鉴权与权限：{base}",
            "description": "无 token / 错误权限时拒绝访问",
            "priority": "P1",
            "module": "安全",
        },
    ]
    need = "确认" not in user and "就这些" not in user
    return {
        "message": "已根据需求生成候选测试点，请确认或补充边界场景。",
        "test_points": points,
        "need_user": need,
        "questions": ["是否需要补充异常流 / 性能相关测试点？"] if need else [],
    }


def mock_test_cases(req: EngineRequest) -> dict[str, Any]:
    user = _last_user(req)
    points = req.artifacts.get("test_points") or []
    titles = [p.get("title", "未命名") for p in points] or [user[:60] or "默认用例"]
    cases = []
    for i, title in enumerate(titles[:5]):
        cases.append(
            {
                "title": f"用例-{i + 1}: {title}",
                "precondition": "服务可用，测试账号已准备",
                "steps": ["准备请求参数", "发送接口请求", "校验响应码与关键字段"],
                "expected": "HTTP 200，业务码成功",
                "priority": "P1",
                "tags": ["AI生成", "接口"],
                "method": "GET",
                "path": "/api/example",
                "assert": {"status_code": 200},
            }
        )
    need = "确认" not in user and "落库" not in user
    return {
        "message": "已按模板生成测试用例草稿，可继续修改或确认。",
        "test_cases": cases,
        "need_user": need,
        "questions": ["请确认优先级与断言是否需要调整？"] if need else [],
    }


def mock_execute_plan(req: EngineRequest) -> dict[str, Any]:
    cases = req.artifacts.get("test_cases") or []
    base = (req.runtime.base_url or "http://127.0.0.1:9").rstrip("/")
    plan = []
    for c in cases or [{"title": "冒烟", "method": "GET", "path": "/", "assert": {"status_code": 200}}]:
        method = (c.get("method") or "GET").upper()
        path = c.get("path") or "/"
        plan.append(
            {
                "case_title": c.get("title") or "case",
                "method": method,
                "url": f"{base}{path if path.startswith('/') else '/' + path}",
                "headers": dict(req.runtime.headers or {}),
                "body": c.get("body"),
                "assert": c.get("assert") or {"status_code": 200},
            }
        )
    return {"message": "执行计划已生成", "plan": plan}


def _last_user(req: EngineRequest) -> str:
    for m in reversed(req.messages):
        if m.role == "user":
            return m.content
    return ""
