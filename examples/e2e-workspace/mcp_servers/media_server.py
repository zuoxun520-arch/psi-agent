"""Media MCP server — image generation, vision understanding, TTS, STT.

All tools call OpenAI-compatible APIs. Configure via environment variables:

    OPENAI_API_KEY      — required
    OPENAI_BASE_URL     — optional (default: https://api.openai.com/v1)
    MEDIA_IMAGE_MODEL   — optional (default: dall-e-3)
    MEDIA_VISION_MODEL  — optional (default: gpt-4o)
    MEDIA_TTS_MODEL     — optional (default: tts-1-hd)
    MEDIA_STT_MODEL     — optional (default: whisper-1)

Start::

    uv run python mcp_servers/media_server.py
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import aiohttp
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("media-mcp", instructions="Image generation, vision understanding, TTS, and STT via OpenAI-compatible APIs")

_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
_IMG_MODEL = os.environ.get("MEDIA_IMAGE_MODEL", "dall-e-3")
_VISION_MODEL = os.environ.get("MEDIA_VISION_MODEL", "gpt-4o")
_TTS_MODEL = os.environ.get("MEDIA_TTS_MODEL", "tts-1-hd")
_STT_MODEL = os.environ.get("MEDIA_STT_MODEL", "whisper-1")

_HEADERS = {"Authorization": f"Bearer {_API_KEY}", "Content-Type": "application/json"}


# ── helpers ────────────────────────────────────────────────────────────────────


async def _post_json(path: str, body: dict[str, Any]) -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{_BASE_URL}{path}", json=body, headers=_HEADERS) as resp:
            if resp.status >= 400:
                text = await resp.text()
                return {"error": f"HTTP {resp.status}: {text[:500]}"}
            return await resp.json()


async def _post_multipart(path: str, data: aiohttp.FormData) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{_BASE_URL}{path}", data=data, headers=headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                return {"error": f"HTTP {resp.status}: {text[:500]}"}
            return await resp.json()


# ── tools ──────────────────────────────────────────────────────────────────────


@mcp.tool(description="Generate an image from a text prompt. Uses free Pollinations.ai by default, falls back to DALL-E if OPENAI_API_KEY is configured and Pollinations fails.")
async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    style: str = "vivid",
    output_path: str = "",
    backend: str = "pollinations",
) -> str:
    """Generate an image from a text prompt.

    By default uses Pollinations.ai (free, no API key, fast).
    Set backend="dalle" to force DALL-E (requires OPENAI_API_KEY).

    Args:
        prompt: Image description. Be specific about subject, style, and composition.
        size: WidthxHeight in pixels. Pollinations: any (default 1024x1024). DALL-E: 1024x1024, 1792x1024, 1024x1792.
        style: Ignored by Pollinations. DALL-E: vivid or natural.
        output_path: Where to save the image. Required — returns the path on success.
        backend: "pollinations" (default, free) or "dalle" (needs OPENAI_API_KEY).
    """
    import anyio
    import urllib.parse

    # ── Pollinations.ai (highest priority, free, no API key) ─────────────────
    if backend == "pollinations":
        try:
            w, h = 1024, 1024
            parts = size.lower().replace(" ", "").split("x")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                w, h = int(parts[0]), int(parts[1])

            encoded = urllib.parse.quote(prompt, safe="")
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        return f"[Error] Pollinations.ai returned HTTP {resp.status}: {text[:300]}"
                    image_bytes = await resp.read()

            if not output_path:
                output_path = "generated_image.png"

            path = anyio.Path(output_path)
            await path.parent.mkdir(parents=True, exist_ok=True)

            # Pollinations returns JPEG; convert to PNG for consistency
            content_type = "image/jpeg"
            if image_bytes[:4] == b"\x89PNG":
                content_type = "image/png"

            if content_type == "image/jpeg":
                try:
                    from PIL import Image
                    import io

                    img = Image.open(io.BytesIO(image_bytes))
                    if output_path.endswith(".jpg") or output_path.endswith(".jpeg"):
                        await path.write_bytes(image_bytes)
                    else:
                        img.save(str(path), "PNG")
                except Exception:
                    await path.write_bytes(image_bytes)
            else:
                await path.write_bytes(image_bytes)

            size_kb = len(image_bytes) // 1024
            return f"[OK] Image generated via Pollinations.ai ({w}x{h}, {size_kb} KB) → {output_path}"

        except Exception as e:
            pollinations_error = str(e)
            # Fall through to DALL-E if available
            if not _API_KEY:
                return f"[Error] Pollinations.ai failed: {pollinations_error}. Set OPENAI_API_KEY to use DALL-E fallback."
            # else: continue to DALL-E below

    # ── DALL-E fallback ──────────────────────────────────────────────────────
    if not _API_KEY:
        return "[Error] OPENAI_API_KEY is not set and Pollinations.ai is unavailable."

    dalle_size = size if size in ("1024x1024", "1792x1024", "1024x1792") else "1024x1024"
    body = {
        "model": _IMG_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": dalle_size,
        "style": style if style in ("vivid", "natural") else "vivid",
        "response_format": "b64_json",
    }
    result = await _post_json("/images/generations", body)

    if "error" in result:
        return f"[Error] Both Pollinations.ai and DALL-E failed. DALL-E: {result['error']}"

    b64 = result.get("data", [{}])[0].get("b64_json", "")
    revised = result.get("data", [{}])[0].get("revised_prompt", "")

    if not b64:
        return f"[Error] No image data in DALL-E response"

    if not output_path:
        output_path = "generated_image.png"

    path = anyio.Path(output_path)
    await path.parent.mkdir(parents=True, exist_ok=True)
    await path.write_bytes(base64.b64decode(b64))
    return f"[OK] Image generated via DALL-E → {output_path}" + (f"\nRevised prompt: {revised}" if revised else "")


@mcp.tool(description="Analyze an image using a vision-capable model (GPT-4o). Provide an image path and a question about it.")
async def understand_image(image_path: str, question: str = "Describe this image in detail.") -> str:
    """Understand and describe an image using a vision model.

    Args:
        image_path: Path to the image file (PNG, JPG, GIF, WEBP).
        question: What to ask about the image.
    """
    if not _API_KEY:
        return "[Error] OPENAI_API_KEY is not set"

    try:
        import anyio

        path = anyio.Path(image_path)
        if not await path.exists():
            return f"[Error] Image not found: {image_path}"
        image_bytes = await path.read_bytes()
    except Exception as e:
        return f"[Error] Failed to read image: {e}"

    ext = image_path.rsplit(".", 1)[-1].lower()
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/png")

    b64 = base64.b64encode(image_bytes).decode()
    body = {
        "model": _VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                ],
            }
        ],
        "max_tokens": 1024,
    }
    result = await _post_json("/chat/completions", body)

    if "error" in result:
        return f"[Error] Vision request failed: {result['error']}"

    return result.get("choices", [{}])[0].get("message", {}).get("content", "[No response]")


@mcp.tool(description="Convert text to speech using OpenAI TTS. Saves audio to a file and returns the path.")
async def text_to_speech(
    text: str,
    voice: str = "alloy",
    speed: float = 1.0,
    output_path: str = "",
) -> str:
    """Convert text to speech and save as MP3.

    Args:
        text: Text to convert (max 4096 chars).
        voice: alloy, echo, fable, onyx, nova, or shimmer.
        speed: Playback speed 0.25–4.0.
        output_path: Where to save the MP3 file. Defaults to workspace/tts_output.mp3.
    """
    if not _API_KEY:
        return "[Error] OPENAI_API_KEY is not set"
    if output_path == "":
        output_path = "tts_output.mp3"

    body = {"model": _TTS_MODEL, "input": text, "voice": voice, "speed": speed, "response_format": "mp3"}
    headers = {"Authorization": f"Bearer {_API_KEY}", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{_BASE_URL}/audio/speech", json=body, headers=headers) as resp:
            if resp.status >= 400:
                text_err = await resp.text()
                return f"[Error] TTS failed: HTTP {resp.status}: {text_err[:500]}"
            audio_bytes = await resp.read()

    try:
        import anyio

        path = anyio.Path(output_path)
        await path.parent.mkdir(parents=True, exist_ok=True)
        await path.write_bytes(audio_bytes)
        return f"[OK] Audio saved to {output_path} ({len(audio_bytes)} bytes)"
    except Exception as e:
        return f"[Error] Failed to save audio: {e}"


@mcp.tool(description="Transcribe speech to text using OpenAI Whisper. Provide an audio file path and get the transcription.")
async def speech_to_text(
    audio_path: str,
    language: str = "",
    response_format: str = "text",
) -> str:
    """Transcribe an audio file to text using Whisper.

    Args:
        audio_path: Path to the audio file (MP3, WAV, M4A, WEBM, etc., max 25 MB).
        language: ISO-639-1 language code (e.g. zh, en, ja). Empty for auto-detect.
        response_format: text, json, srt, or verbose_json.
    """
    if not _API_KEY:
        return "[Error] OPENAI_API_KEY is not set"

    try:
        import anyio

        path = anyio.Path(audio_path)
        if not await path.exists():
            return f"[Error] Audio file not found: {audio_path}"
        file_size = await anyio.Path(audio_path).stat()
        if hasattr(file_size, "st_size") and file_size.st_size > 25 * 1024 * 1024:
            return "[Error] Audio file exceeds 25 MB limit"
    except Exception as e:
        return f"[Error] Failed to check audio file: {e}"

    data = aiohttp.FormData()
    data.add_field("model", _STT_MODEL)
    if language:
        data.add_field("language", language)
    data.add_field("response_format", response_format)

    try:
        from pathlib import Path as SyncPath  # only for sync file open in FormData
    except Exception:
        import anyio

        data.add_field("file", open(audio_path, "rb"), filename=audio_path.rsplit("/", 1)[-1])
        result = await _post_multipart("/audio/transcriptions", data)
        if "file" in str(type(data)):
            pass  # FormData manages cleanup
        if isinstance(result, dict) and "error" in result:
            return f"[Error] Transcription failed: {result['error']}"
        return json.dumps(result, ensure_ascii=False) if response_format == "json" else str(result.get("text", result))

    data.add_field("file", open(audio_path, "rb"), filename=audio_path.rsplit("/", 1)[-1] or "audio.mp3")
    result = await _post_multipart("/audio/transcriptions", data)

    if isinstance(result, dict) and "error" in result:
        return f"[Error] Transcription failed: {result['error']}"

    if response_format == "json" or response_format == "verbose_json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result.get("text", result))


# ── entry ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
