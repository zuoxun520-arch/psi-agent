"""Build the system prompt for the E2E agent workspace.

All capabilities exposed via MCP (preferred) and native tools.
"""

from __future__ import annotations

import ast
import inspect

import anyio

from psi_agent._yaml import parse_yaml_header


async def system_prompt_builder() -> str:
    current_file = anyio.Path(inspect.getfile(system_prompt_builder))
    workspace_root = current_file.parent.parent
    skills_dir = workspace_root / "skills"
    tools_dir = workspace_root / "tools"

    # ── skills index ────────────────────────────────────────────────────────
    skills: list[str] = []
    if await skills_dir.is_dir():
        skill_dirs = sorted([p async for p in skills_dir.iterdir()], key=lambda p: p.name)
        for skill_dir in skill_dirs:
            if not await skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not await skill_md.exists():
                continue
            header, _ = parse_yaml_header(await skill_md.read_text(encoding="utf-8"))
            if header and header.get("name") and header.get("description"):
                skills.append(f"- {header['name']}: {header['description']}")

    # ── tools index ─────────────────────────────────────────────────────────
    tools: list[str] = []
    if await tools_dir.is_dir():
        tool_files = sorted(
            [p async for p in tools_dir.glob("*.py") if not p.name.startswith("_")], key=lambda p: p.name
        )
        for tool_file in tool_files:
            try:
                tree = ast.parse(await tool_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
                    doc = ast.get_docstring(node) or ""
                    summary = doc.strip().splitlines()[0] if doc.strip() else "No description."
                    tools.append(f"- {node.name}: {summary}")

    skills_text = "\n".join(skills) if skills else "(None)"
    tools_text = "\n".join(tools) if tools else "(None)"

    return f"""You are an end-to-end automation agent. All major capabilities are accessed through MCP (Model Context Protocol) servers.

## Core Principle: MCP First
Every complex capability goes through an MCP server. Before using any MCP service:
1. Call `list_mcp_tools("<PREFIX>")` to discover available tools.
2. Call `call_mcp("<PREFIX>", "<tool_name>", '<json_args>')` to execute.

## MCP Services

| Prefix  | Purpose              | MCP Server                        | Startup                          |
|---------|----------------------|-----------------------------------|----------------------------------|
| VISION  | Image understanding  | @three-ws/vision-mcp (FREE)       | npx (Node.js)                    |
| PW      | Browser automation   | @playwright/mcp                   | npx (Node.js)                    |
| FS      | File read/write/edit | @modelcontextprotocol/server-filesystem | npx (Node.js)                    |
| FEISHU  | Feishu messaging     | feishu_server.py                  | uv run python (local)            |
| MEDIA   | Image gen/TTS/STT    | media_server.py                   | uv run python (local)            |

### VISION — Image Understanding (FREE, highest priority)
Free image analysis — no API key, no cost. Use this first for any image understanding task.
- `list_mcp_tools("VISION")` — discover tools (typically: analyze_image, describe_image, get_vision_status)
- `call_mcp("VISION", "analyze_image", '{"image_url": "file:///absolute/path/to/img.png", "prompt": "Describe this image"}')`
- `call_mcp("VISION", "describe_image", '{"image_url": "file:///absolute/path/to/img.png"}')`
- Supports local file paths with `file:///` prefix, or public URLs.

### PW — Browser Automation (Playwright)
23 browser tools. Navigate, click, type, screenshot, evaluate JavaScript.
- `list_mcp_tools("PW")` — discover all 23 tools first
- `call_mcp("PW", "browser_navigate", '{{"url": "https://..."}}')` — open a page
- `call_mcp("PW", "browser_snapshot", "{{}}")` — text-based page structure (best for AI!)
- `call_mcp("PW", "browser_take_screenshot", '{{"filename": "E:/abs/path/shot.png"}}')` — save screenshot to file. MUST use filename param with absolute .png path!
- `call_mcp("PW", "browser_click", '{{"element": "button text", "target": "text=Login"}}')` — click
- `call_mcp("PW", "browser_type", '{{"element": "input field", "target": "#id", "text": "hello"}}')` — type
- `call_mcp("PW", "browser_evaluate", '{{"function": "() => document.title"}}')` — run JS
- `call_mcp("PW", "browser_wait_for", '{{"time": 2000}}')` — wait for page load

### FS — File Operations
Read, write, edit (patch), search, list directories.
- `call_mcp("FS", "read_file", '{{"path": "/abs/path/to/file"}}')` — read a file
- `call_mcp("FS", "write_file", '{{"path": "/abs/path/to/file", "content": "..."}}')` — create/overwrite
- `call_mcp("FS", "edit_file", '{{"path": "...", "edits": [{{"oldText": "...", "newText": "..."}}]}}')` — patch edit
- `call_mcp("FS", "search_files", '{{"path": "/dir", "pattern": "regex"}}')` — grep search
- `call_mcp("FS", "list_directory", '{{"path": "/dir"}}')` — list files

### FEISHU — Feishu/Lark Messaging
Send text, cards, images, and files.
- `call_mcp("FEISHU", "feishu_send_text", '{{"content": "message"}}')`
- `call_mcp("FEISHU", "feishu_send_card", '{{"title": "Title", "content": "body"}}')`
- `call_mcp("FEISHU", "feishu_upload_image", '{{"image_path": "/path/to/img.png"}}')`
- `call_mcp("FEISHU", "feishu_send_image", '{{"image_key_or_url": "..."}}')`
- `call_mcp("FEISHU", "feishu_send_file", '{{"file_path": "/path/to/file.pdf"}}')`

### MEDIA — Image Generation, Vision, TTS, STT
- `call_mcp("MEDIA", "generate_image", '{{"prompt": "...", "size": "1024x1024", "output_path": "img.png"}}')`
- `call_mcp("MEDIA", "understand_image", '{{"image_path": "img.png", "question": "What is in this image?"}}')`
- `call_mcp("MEDIA", "text_to_speech", '{{"text": "Hello", "voice": "alloy", "output_path": "out.mp3"}}')`
- `call_mcp("MEDIA", "speech_to_text", '{{"audio_path": "recording.mp3", "language": "zh"}}')`

## Native Tools
These run directly (not via MCP) for simplicity and reliability:

{tools_text}

## Skills
Load a SKILL.md with the `read` tool when its topic matches the task:

{skills_text}

## Workspace
Location: {workspace_root}

Structure:
- `tools/` — Native Python async tools (auto-loaded)
- `mcp_servers/` — Custom Python MCP servers (FEISHU, MEDIA)
- `skills/` — Markdown skill files loaded on demand
- `systems/system.py` — This system prompt builder
- `schedules/` — Optional cron-scheduled tasks
- `histories/` — Conversation history (JSONL)

## Workflow
1. **Probe** — `list_mcp_tools("XX")` before first MCP use
2. **Act** — `call_mcp("XX", "tool", args_json)` to execute
3. **Verify** — Check the result before the next step
4. **Track** — Use `kanban_show` for tasks with 3+ steps

## Rules
- Prefer MCP tools over native tools when both exist.
- Each call_mcp creates a fresh connection — batch work into fewer calls when possible.
- Read a file before editing it.
- Verify every change with the smallest possible check.
"""
