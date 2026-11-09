from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class McpError(RuntimeError):
    pass


async def _jsonrpc(url: str, method: str, params: dict[str, Any] | None, headers: dict[str, str]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **(headers or {})}
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=hdrs)
        if resp.status_code >= 400:
            raise McpError(f"HTTP {resp.status_code}: {resp.text[:400]}")
        ct = (resp.headers.get("content-type") or "").lower()
        if "text/event-stream" in ct:
            last: dict[str, Any] | None = None
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    if not raw:
                        continue
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
        raise McpError("stdio transport is not supported in engine execution")
    if not (url or "").strip():
        raise McpError("MCP url is required")
    headers = headers or {}
    try:
        await _jsonrpc(
            url,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ai-test-engine", "version": "0.1.0"},
            },
            headers,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("MCP initialize skipped/failed: %s", exc)
    return await _jsonrpc(url, "tools/call", {"name": tool_name, "arguments": arguments or {}}, headers)


def resolve_server(mcp_servers: list[dict[str, Any]], hook: dict[str, Any]) -> dict[str, Any] | None:
    sid = hook.get("server_id")
    sname = hook.get("server_name")
    for srv in mcp_servers or []:
        if sid and srv.get("id") == sid:
            return srv
        if sname and srv.get("name") == sname:
            return srv
    if len(mcp_servers or []) == 1:
        return mcp_servers[0]
    return None
