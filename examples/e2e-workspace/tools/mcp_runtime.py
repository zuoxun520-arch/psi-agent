"""MCP bridge with connection pooling — v2.

Pooled connections survive across tool calls within a session turn.
Stateful MCP servers (Playwright) keep browser pages alive.
All connections auto-close on idle timeout, session shutdown, or hot-reload.
"""

from __future__ import annotations

import atexit
import json
import os
import shlex
import subprocess
import sys
import time
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent


class MCPConfigError(RuntimeError):
    pass


# ── connection pool ──────────────────────────────────────────────────────────

_POOL: dict[str, dict[str, Any]] = {}
_IDLE_TTL: float = 300.0  # close idle connections after 5 minutes


class _Session:
    """Thin async context manager for transport + ClientSession."""

    def __init__(self, opener: Any) -> None:
        self._opener = opener
        self._transport_cm: Any = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> ClientSession:
        self._transport_cm = self._opener()
        read, write, *_ = await self._transport_cm.__aenter__()
        self._session = ClientSession(read, write)
        return await self._session.__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        if self._session is not None:
            await self._session.__aexit__(*args)
        if self._transport_cm is not None:
            await self._transport_cm.__aexit__(*args)


def _new_transport(prefix: str) -> _Session:
    """Create a fresh transport for *prefix* from environment config."""
    cfg = _config(prefix)
    return _connect(cfg)


async def _get_or_create(prefix: str) -> ClientSession:
    """Return a ready, initialized ClientSession from the pool."""
    key = prefix.upper()
    now = time.monotonic()

    # reap idle connections
    stale = [k for k, v in _POOL.items() if now - v.get("last_used", now) > _IDLE_TTL]
    for k in stale:
        await _close_one(k)

    if key in _POOL:
        entry = _POOL[key]
        entry["last_used"] = now
        # already initialized — skip duplicate init
        return entry["session"]

    transport = _new_transport(prefix)
    try:
        session = await transport.__aenter__()
        await session.initialize()
    except BaseException:
        # P0: cleanup transport on failure, then pop
        try:
            await transport.__aexit__(None, None, None)
        except Exception:
            pass
        raise

    _POOL[key] = {
        "transport": transport,
        "session": session,
        "initialized": True,
        "last_used": now,
    }
    return session


async def _close_one(key: str) -> None:
    """Close and remove one pooled connection. Safe to call on missing keys."""
    entry = _POOL.pop(key, None)
    if entry is None:
        return
    try:
        await entry["transport"].__aexit__(None, None, None)
    except Exception:
        pass


async def close_mcp(prefix: str) -> str:
    """Close persistent MCP connection(s).

    Args:
        prefix: Prefix to close, or "*" to close all.
    """
    if prefix == "*":
        keys = list(_POOL)
        for k in keys:
            await _close_one(k)
        return f"[OK] Closed {len(keys)} MCP connection(s)"
    if prefix.upper() not in _POOL:
        return f"[Error] No active connection: {prefix}"
    await _close_one(prefix.upper())
    return f"[OK] Closed MCP: {prefix}"


# ── config (env vars) ────────────────────────────────────────────────────────


def _split_args(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("["):
        loaded = json.loads(value)
        if isinstance(loaded, list):
            return [str(v) for v in loaded]
    return shlex.split(value, posix=False)


def _config(prefix: str) -> dict[str, Any]:
    p = prefix.upper()
    raw = os.environ.get(f"MCP_{p}_CONFIG", "").strip()
    if raw:
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise MCPConfigError(f"MCP_{p}_CONFIG must be a JSON object")
        return loaded

    transport = os.environ.get(f"MCP_{p}_TRANSPORT", "stdio").strip().lower()
    url = os.environ.get(f"MCP_{p}_URL", "").strip()
    command = os.environ.get(f"MCP_{p}_COMMAND", "").strip()
    args = _split_args(os.environ.get(f"MCP_{p}_ARGS", ""))
    env_raw = os.environ.get(f"MCP_{p}_ENV", "").strip()
    env: dict[str, str] | None = None
    if env_raw:
        loaded = json.loads(env_raw)
        if isinstance(loaded, dict):
            env = {str(k): str(v) for k, v in loaded.items()}

    if transport in {"http", "streamable_http", "streamable-http"}:
        if not url:
            raise MCPConfigError(f"MCP_{p}_URL is required for HTTP MCP transport")
        return {"transport": "http", "url": url}
    if transport == "sse":
        if not url:
            raise MCPConfigError(f"MCP_{p}_URL is required for SSE MCP transport")
        return {"transport": "sse", "url": url}
    if not command:
        raise MCPConfigError(
            f"MCP_{p}_COMMAND is not set. Set MCP_{p}_COMMAND and optional MCP_{p}_ARGS, "
            f"or set MCP_{p}_TRANSPORT=http with MCP_{p}_URL."
        )
    return {"transport": "stdio", "command": command, "args": args, "env": env}


def _connect(cfg: dict[str, Any]) -> _Session:
    transport = str(cfg.get("transport", "stdio")).lower().replace("-", "_")
    if transport == "stdio":
        params = StdioServerParameters(
            command=str(cfg["command"]),
            args=[str(v) for v in cfg.get("args", [])],
            env=cfg.get("env") or None,
        )
        return _Session(lambda: stdio_client(params, errlog=subprocess.DEVNULL))
    if transport == "sse":
        return _Session(lambda: sse_client(str(cfg["url"])))
    if transport in {"http", "streamable_http"}:
        return _Session(lambda: streamable_http_client(str(cfg["url"])))
    raise MCPConfigError(f"Unsupported MCP transport: {transport}")


def _format_result(result: Any) -> str:
    parts = [block.text for block in getattr(result, "content", []) if isinstance(block, TextContent) and block.text]
    if parts:
        return ("Error: " if getattr(result, "isError", False) else "") + "\n".join(parts)
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)
    return ("Error: " if getattr(result, "isError", False) else "") + str(result)


# ── public tools ─────────────────────────────────────────────────────────────


async def call_mcp(prefix: str, tool_name: str, args_json: str = "{}") -> str:
    """Call a tool on an MCP server. Connections survive across calls — browser pages persist!

    Available MCP prefixes:
    - PW     → Playwright browser (navigate, click, type, screenshot, snapshot, evaluate...)
    - FS     → Filesystem (read, write, edit, search, list directory)
    - VISION → FREE image understanding (analyze, describe — no API key)
    - MEDIA  → Image generation (free Pollinations.ai) + TTS + STT
    - FEISHU → Feishu messaging (send text, cards, images, files)

    Args:
        prefix: MCP server prefix, e.g. "PW" for Playwright.
        tool_name: Tool to call. Discover with list_mcp_tools first.
        args_json: Arguments as JSON string, e.g. '{"url": "https://example.com"}'.

    Examples:
        call_mcp("PW", "browser_navigate", '{"url": "https://example.com"}')
        call_mcp("PW", "browser_snapshot", "{}")    # read page content
        call_mcp("PW", "browser_take_screenshot", '{"filename": "E:/shot.png"}')
    """
    try:
        args = json.loads(args_json or "{}")
        if not isinstance(args, dict):
            return "[Error] args_json must decode to an object"
        session = await _get_or_create(prefix)
        result = await session.call_tool(tool_name, args)
        return _format_result(result)
    except Exception as exc:
        # P0: cleanup on error so next call starts fresh
        await _close_one(prefix.upper())
        return f"[MCP Error] {exc}"


# ── lifecycle hooks ──────────────────────────────────────────────────────────


def _cleanup_sync() -> None:
    """Synchronous wrapper for atexit / hot-reload cleanup.

    Finds the running event loop, schedules ``_cleanup_all()``, and
    blocks until it completes.  Best-effort — failures are logged but
    never re-raised (cleanup must never crash the process).
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # no event loop, nothing to clean up

    async def _go() -> None:
        try:
            keys = list(_POOL)
            for k in keys:
                await _close_one(k)
        except Exception:
            pass

    try:
        asyncio.ensure_future(_go())
    except Exception:
        pass


# P1: clean up old pooled connections when the module is hot-reloaded.
# ToolRegistry re-executes this file under a new module name when the
# file hash changes, but the OLD module's connections are orphaned.
# We detect existing modules for the same file path and tear them down.
_this_file = __file__ or ""
if _this_file:
    for _mn in list(sys.modules):
        _mod = sys.modules.get(_mn)
        if _mod is not None and getattr(_mod, "__file__", "") == _this_file and _mn != __name__:
            _cleanup = getattr(_mod, "_cleanup_sync", None)
            if _cleanup is not None:
                try:
                    _cleanup()
                except Exception:
                    pass

# P1: session process shutdown — atexit fires when the Python process exits.
atexit.register(_cleanup_sync)


async def list_mcp_tools(prefix: str) -> str:
    """Discover all tools on an MCP server. Call this first when exploring a new prefix.

    Available prefixes: PW (Playwright browser), FS (filesystem),
    VISION (FREE image understanding), MEDIA (image gen/TTS/STT), FEISHU (Feishu).

    Args:
        prefix: MCP prefix. Must match an MCP_{PREFIX}_COMMAND env var.

    Example:
        list_mcp_tools("PW") → lists all Playwright browser tools
    """
    try:
        session = await _get_or_create(prefix)
        tools = (await session.list_tools()).tools
        lines = [f"- {tool.name}: {tool.description or ''}" for tool in tools]
        return "\n".join(lines) if lines else "[No MCP tools]"
    except Exception as exc:
        await _close_one(prefix.upper())
        return f"[MCP Error] {exc}"
