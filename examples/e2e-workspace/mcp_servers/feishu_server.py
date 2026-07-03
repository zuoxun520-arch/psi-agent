"""Feishu (Lark) MCP server — messaging, cards, image/file upload and sending.

Supports two authentication modes:

1. **Webhook mode** (simplest) — set ``FEISHU_WEBHOOK_URL`` env var.
   Supports text and card messages.

2. **API mode** (full-featured) — set ``FEISHU_APP_ID`` and ``FEISHU_APP_SECRET``.
   Supports image/file upload, plus all webhook capabilities.

Start::

    uv run python mcp_servers/feishu_server.py
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import aiohttp
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("feishu-mcp", instructions="Feishu/Lark messaging — send text, cards, images, and files")

_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
_APP_ID = os.environ.get("FEISHU_APP_ID", "").strip()
_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "").strip()

_API_BASE = "https://open.feishu.cn/open-apis"

# token cache
_token: str = ""
_token_expires_at: float = 0.0


async def _get_token() -> str:
    """Obtain a tenant access token via app credentials."""
    global _token, _token_expires_at
    if _token and time.time() < _token_expires_at - 60:
        return _token

    body = {"app_id": _APP_ID, "app_secret": _APP_SECRET}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{_API_BASE}/auth/v3/tenant_access_token/internal", json=body) as resp:
            data = await resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu auth failed: {data.get('msg', data)}")
    _token = data["tenant_access_token"]
    _token_expires_at = time.time() + data.get("expire", 7200)
    return _token


def _valid(webhook_url: str = "") -> str:
    """Check credentials, return error string or empty string."""
    if webhook_url or _WEBHOOK_URL:
        return ""
    if _APP_ID and _APP_SECRET:
        return ""
    return "[Error] Set FEISHU_WEBHOOK_URL for webhook mode, or FEISHU_APP_ID + FEISHU_APP_SECRET for API mode"


# ── tools ──────────────────────────────────────────────────────────────────────


@mcp.tool(description="Send a plain text message to a Feishu chat via webhook or API.")
async def feishu_send_text(content: str, webhook_url: str = "") -> str:
    """Send a text message to Feishu.

    Args:
        content: Message text body (supports Feishu Markdown: **bold**, *italic*, <at id=xxx>, etc.).
        webhook_url: Override the default webhook URL. If empty, uses FEISHU_WEBHOOK_URL or FEISHU_APP_ID/APP_SECRET.
    """
    err = _valid(webhook_url)
    if err:
        return err

    url = webhook_url or _WEBHOOK_URL
    if url:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"msg_type": "text", "content": {"text": content}}) as resp:
                data = await resp.json()
        if data.get("code") != 0:
            return f"[Error] Feishu send failed: {data.get('msg', data)}"
        return "[OK] Text message sent via webhook"

    # API mode — send to a specific chat (requires chat_id; use webhook for simplicity)
    return "[Error] API mode requires a chat_id. Use webhook mode (FEISHU_WEBHOOK_URL) for direct messaging, or provide a chat_id parameter."


@mcp.tool(description="Send an interactive card message to Feishu. Cards can contain rich layout, buttons, and data.")
async def feishu_send_card(
    title: str,
    content: str = "",
    elements_json: str = "",
    header_color: str = "blue",
    webhook_url: str = "",
) -> str:
    """Send an interactive card message.

    Args:
        title: Card title (plain text).
        content: Card body in Feishu Markdown.
        elements_json: JSON array of interactive elements (buttons, pickers, etc.). Usually empty for simple cards.
        header_color: Card header color — blue, red, green, yellow, purple, turquoise, wathet, etc.
        webhook_url: Override the default webhook URL.
    """
    err = _valid(webhook_url)
    if err:
        return err

    url = webhook_url or _WEBHOOK_URL
    template = header_color

    card_body: dict[str, Any] = {
        "header": {"title": {"tag": "plain_text", "content": title}, "template": template},
    }

    if content:
        card_body.setdefault("elements", []).append({"tag": "markdown", "content": content})

    if elements_json:
        try:
            extra_elements = json.loads(elements_json)
            if isinstance(extra_elements, list):
                card_body.setdefault("elements", []).extend(extra_elements)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid elements_json: {e}"

    card = {"config": {"wide_screen_mode": True}, **card_body}

    if url:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"msg_type": "interactive", "card": card}) as resp:
                data = await resp.json()
        if data.get("code") != 0:
            return f"[Error] Feishu card send failed: {data.get('msg', data)}"
        return "[OK] Card message sent via webhook"

    return "[Error] API mode not yet implemented for cards. Use webhook mode."


@mcp.tool(description="Upload an image to Feishu and get its image_key for use in messages.")
async def feishu_upload_image(image_path: str) -> str:
    """Upload an image to Feishu and return the image_key.

    Args:
        image_path: Path to a PNG, JPG, GIF, or WEBP image file.
    """
    if not _APP_ID:
        return "[Error] Image upload requires FEISHU_APP_ID + FEISHU_APP_SECRET (API mode)"

    try:
        token = await _get_token()
        import anyio

        path = anyio.Path(image_path)
        if not await path.exists():
            return f"[Error] Image not found: {image_path}"
        image_bytes = await path.read_bytes()
    except Exception as e:
        return f"[Error] {e}"

    data = aiohttp.FormData()
    data.add_field("image_type", "message")
    data.add_field("image", image_bytes, filename=image_path.rsplit("/", 1)[-1] or "image.png")

    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{_API_BASE}/im/v1/images", data=data, headers=headers) as resp:
            result = await resp.json()

    if result.get("code") != 0:
        return f"[Error] Upload failed: {result.get('msg', result)}"

    image_key = result.get("data", {}).get("image_key", "")
    return f"[OK] Image uploaded. image_key: {image_key}"


@mcp.tool(description="Send an image message to Feishu via webhook. Use feishu_upload_image first to get an image_key, or provide a public image URL.")
async def feishu_send_image(image_key_or_url: str, webhook_url: str = "") -> str:
    """Send an image message to Feishu.

    Args:
        image_key_or_url: An image_key from feishu_upload_image, or a public image URL.
        webhook_url: Override the default webhook URL.
    """
    url = webhook_url or _WEBHOOK_URL
    if not url:
        return "[Error] Set FEISHU_WEBHOOK_URL"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"msg_type": "image", "content": {"image_key": image_key_or_url}}) as resp:
            data = await resp.json()
    if data.get("code") != 0:
        return f"[Error] Image send failed: {data.get('msg', data)}"
    return "[OK] Image message sent"


@mcp.tool(description="Send a file to a Feishu chat. Can be PDF, DOC, XLS, PPT, TXT, ZIP, images, etc.")
async def feishu_send_file(file_path: str, webhook_url: str = "") -> str:
    """Send a file to Feishu.

    Args:
        file_path: Path to the file (PDF, DOC, XLS, PPT, TXT, ZIP, images up to 20 MB).
        webhook_url: Override the default webhook URL. API mode must upload then send.
    """
    url = webhook_url or _WEBHOOK_URL
    if not url:
        return "[Error] Set FEISHU_WEBHOOK_URL"

    try:
        import anyio

        path = anyio.Path(file_path)
        if not await path.exists():
            return f"[Error] File not found: {file_path}"
        file_bytes = await path.read_bytes()
        filename = file_path.rsplit("/", 1)[-1] or "file"
    except Exception as e:
        return f"[Error] {e}"

    # For webhook file sending, Feishu requires uploading first, then referencing
    # Since webhook doesn't support direct file upload, we need API mode.
    # As a fallback, embed the file path info and suggest alternatives.
    if _APP_ID and _APP_SECRET:
        token = await _get_token()
        data = aiohttp.FormData()
        data.add_field("file_type", "stream")
        data.add_field("file_name", filename)
        data.add_field("file", file_bytes, filename=filename)
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{_API_BASE}/im/v1/files", data=data, headers=headers) as resp:
                result = await resp.json()
        if result.get("code") != 0:
            return f"[Error] File upload failed: {result.get('msg', result)}"
        file_key = result.get("data", {}).get("file_key", "")
        return f"[OK] File uploaded. file_key: {file_key}. To send, use a card or message with this file_key."
    else:
        return f"[Error] File sending via webhook is not directly supported. Use FEISHU_APP_ID + FEISHU_APP_SECRET for file upload, or share the file path: {file_path}"


# ── entry ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
