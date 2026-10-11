from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


class MessageStreamExtractor:
    """Incrementally extract top-level JSON string field \"message\" while tokens arrive."""

    _KEY = re.compile(r'"message"\s*:\s*"')

    def __init__(self) -> None:
        self._raw = ""
        self._pos = 0
        self._phase = "find_key"  # find_key | in_string | unicode | done
        self._escape = False
        self._unicode_buf = ""

    def feed(self, chunk: str) -> str:
        if not chunk or self._phase == "done":
            return ""
        self._raw += chunk
        out: list[str] = []
        while True:
            if self._phase == "find_key":
                m = self._KEY.search(self._raw)
                if not m:
                    return "".join(out)
                self._pos = m.end()
                self._phase = "in_string"
                continue
            if self._phase == "done":
                return "".join(out)
            if self._pos >= len(self._raw):
                return "".join(out)

            ch = self._raw[self._pos]
            self._pos += 1

            if self._phase == "unicode":
                self._unicode_buf += ch
                if len(self._unicode_buf) == 4:
                    try:
                        out.append(chr(int(self._unicode_buf, 16)))
                    except ValueError:
                        out.append("\\u" + self._unicode_buf)
                    self._unicode_buf = ""
                    self._phase = "in_string"
                continue

            if self._escape:
                self._escape = False
                if ch == "u":
                    self._phase = "unicode"
                    self._unicode_buf = ""
                    continue
                mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}
                out.append(mapping.get(ch, ch))
                continue

            if ch == "\\":
                self._escape = True
            elif ch == '"':
                self._phase = "done"
            else:
                out.append(ch)


def _chunk_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


async def stream_json(
    system: str,
    user: str,
    model: Optional[str] = None,
) -> AsyncIterator[tuple[str, Any]]:
    """Stream OpenAI-compatible chat tokens, then yield parsed JSON.

    Yields:
      ("token", delta_str) for each model chunk
      ("result", dict) once when the full JSON object is parsed
    """
    if not settings.llm_enabled:
        logger.info("LLM disabled (empty API key) → caller may use mock")
        yield ("result", {})
        return

    api_model = model if (settings.allow_model_override and model) else settings.openai_model
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(
                content=system + "\n\n必须只输出合法 JSON 对象，不要 Markdown。字段 message 请放在最前以便流式展示。"
            ),
            HumanMessage(content=user),
        ]
        common = dict(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url.rstrip("/"),
            model=api_model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=1,
            streaming=True,
        )

        text_parts: list[str] = []
        yielded_tokens = False
        try:
            llm = ChatOpenAI(**common, model_kwargs={"response_format": {"type": "json_object"}})
            async for chunk in llm.astream(messages):
                delta = _chunk_text(getattr(chunk, "content", None))
                if delta:
                    yielded_tokens = True
                    text_parts.append(delta)
                    yield ("token", delta)
        except Exception as json_mode_exc:  # noqa: BLE001
            if yielded_tokens:
                raise
            logger.warning("json_object stream failed, retry plain: %s", json_mode_exc)
            llm = ChatOpenAI(**common)
            async for chunk in llm.astream(messages):
                delta = _chunk_text(getattr(chunk, "content", None))
                if delta:
                    text_parts.append(delta)
                    yield ("token", delta)

        text = "".join(text_parts)
        if not text.strip():
            raise LlmError("LLM returned empty stream")
        data = _extract_json(text)
        if not isinstance(data, dict):
            raise LlmError(f"LLM returned non-object JSON: {type(data)}")
        logger.info(
            "LLM stream ok model=%s base=%s keys=%s chars=%s",
            api_model,
            settings.openai_base_url,
            list(data.keys()),
            len(text),
        )
        yield ("result", data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM stream failed model=%s base=%s", api_model, settings.openai_base_url)
        if settings.llm_fallback_mock:
            logger.warning("fallback to mock: %s", exc)
            yield ("result", {})
            return
        raise LlmError(str(exc)) from exc


async def complete_json(system: str, user: str, model: Optional[str] = None) -> dict[str, Any]:
    """Call OpenAI-compatible chat and parse JSON object (non-streaming helper)."""
    data: dict[str, Any] = {}
    async for kind, payload in stream_json(system, user, model=model):
        if kind == "result" and isinstance(payload, dict):
            data = payload
    return data


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
