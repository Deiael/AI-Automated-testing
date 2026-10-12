from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class McpError(RuntimeError):
    pass


async def _jsonrpc(url: str, method: str, params: dict[str, Any] | None, headers: dict[str, str]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **(headers or {})}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=hdrs)
        if resp.status_code >= 400:
            raise McpError(f"HTTP {resp.status_code}: {resp.text[:400]}")
        ct = (resp.headers.get("content-type") or "").lower()
        if "text/event-stream" in ct:
            # Collect last data line from SSE JSON-RPC stream
            last: dict[str, Any] | None = None
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    import json

                    try:
                        last = json.loads(raw)
                    except Exception:  # noqa: BLE001
                        continue
            if not last:
                raise McpError("empty SSE response from MCP server")
            data = last
        else:
            data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        raise McpError(str(err.get("message") or err))
    if isinstance(data, dict) and "result" in data:
        return data["result"]
    return data


async def list_tools(*, transport: str, url: str, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
    transport = (transport or "http").lower()
    if transport == "stdio":
        raise McpError("stdio transport is not supported for remote probe; configure sse/http instead")
    if not url.strip():
        raise McpError("MCP url is required for sse/http transport")
    headers = headers or {}
    try:
        await _jsonrpc(url, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "ai-test-gateway", "version": "0.1.0"}}, headers)
    except Exception as exc:  # noqa: BLE001
        logger.info("MCP initialize skipped/failed: %s", exc)
    result = await _jsonrpc(url, "tools/list", {}, headers)
    tools = result.get("tools") if isinstance(result, dict) else result
    if not isinstance(tools, list):
        return []
    return [t for t in tools if isinstance(t, dict)]


async def call_tool(
    *,
    transport: str,
    url: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    transport = (transport or "http").lower()
    if transport == "stdio":
        raise McpError("stdio transport is not supported for remote call; configure sse/http instead")
    if not url.strip():
        raise McpError("MCP url is required for sse/http transport")
    return await _jsonrpc(
        url,
        "tools/call",
        {"name": tool_name, "arguments": arguments or {}},
        headers or {},
    )
