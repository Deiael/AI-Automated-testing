from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


async def complete_json(system: str, user: str, model: Optional[str] = None) -> dict[str, Any]:
    """Call OpenAI-compatible chat (DeepSeek 等) and parse JSON object."""
    if not settings.llm_enabled:
        logger.info("LLM disabled (empty API key) → caller may use mock")
        return {}

    api_model = model if (settings.allow_model_override and model) else settings.openai_model
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system + "\n\n必须只输出合法 JSON 对象，不要 Markdown。"),
            HumanMessage(content=user),
        ]
        common = dict(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url.rstrip("/"),
            model=api_model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=1,
        )
        try:
            llm = ChatOpenAI(**common, model_kwargs={"response_format": {"type": "json_object"}})
            resp = await llm.ainvoke(messages)
        except Exception as json_mode_exc:  # noqa: BLE001
            logger.warning("json_object mode failed, retry plain: %s", json_mode_exc)
            llm = ChatOpenAI(**common)
            resp = await llm.ainvoke(messages)
        text = resp.content if isinstance(resp.content, str) else str(resp.content)
        data = _extract_json(text)
        if not isinstance(data, dict):
            raise LlmError(f"LLM returned non-object JSON: {type(data)}")
        logger.info("LLM ok model=%s base=%s keys=%s", api_model, settings.openai_base_url, list(data.keys()))
        return data
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM call failed model=%s base=%s", api_model, settings.openai_base_url)
        if settings.llm_fallback_mock:
            logger.warning("fallback to mock: %s", exc)
            return {}
        raise LlmError(str(exc)) from exc


def resolve_api_model(request_model: Optional[str] = None) -> str:
    if settings.allow_model_override and request_model:
        return request_model
    return settings.openai_model


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    return json.loads(text)
