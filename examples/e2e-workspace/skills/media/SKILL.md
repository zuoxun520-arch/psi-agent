---
name: media
description: "Media generation and understanding — image generation (DALL-E), vision analysis, TTS, and STT via OpenAI-compatible APIs."
---

# Media Generation & Understanding

## Image Understanding → VISION MCP (FREE, highest priority)

The `VISION` MCP server (`@three-ws/vision-mcp`) is **free, no API key needed**. Always use it first for image analysis.

```
# Discover tools
call_mcp("VISION", "list_mcp_tools", "")

# Tools: analyze_image, describe_image, get_vision_status
```

### Usage
```
call_mcp("VISION", "analyze_image", '{"image_url": "file:///E:/path/to/image.png", "prompt": "Describe this image"}')
call_mcp("VISION", "describe_image", '{"image_url": "file:///E:/path/to/image.png"}')
```

## Image Generation / TTS / STT → MEDIA MCP

Use the MEDIA MCP server for image generation, text-to-speech, and speech-to-text. Image understanding is also available as fallback if VISION MCP is unavailable.

```
# Discover tools
call_mcp("MEDIA", "list_mcp_tools", "")

# Tools: generate_image, understand_image (fallback), text_to_speech, speech_to_text
```

## Image Generation

```
# Basic generation
call_mcp("MEDIA", "generate_image", '{"prompt": "A cat sitting on a laptop in a coffee shop, watercolor style", "size": "1024x1024", "output_path": "cat_coffee.png"}')

# Landscape orientation
call_mcp("MEDIA", "generate_image", '{"prompt": "Futuristic city skyline at sunset", "size": "1792x1024", "style": "vivid", "output_path": "city.png"}')

# Portrait orientation, natural style
call_mcp("MEDIA", "generate_image", '{"prompt": "Portrait of a woman in a garden", "size": "1024x1792", "style": "natural", "output_path": "portrait.png"}')
```

### Size options
- `1024x1024` — square (default)
- `1792x1024` — landscape
- `1024x1792` — portrait

### Style options
- `vivid` — hyper-real, dramatic (default)
- `natural` — more realistic, less stylized

## Image Understanding (Vision)

```
# Basic description
call_mcp("MEDIA", "understand_image", '{"image_path": "photo.jpg", "question": "Describe this image in detail."}')

# Specific analysis
call_mcp("MEDIA", "understand_image", '{"image_path": "screenshot.png", "question": "What error message is shown? What is the exact text?"}')

# Extract text (OCR-like)
call_mcp("MEDIA", "understand_image", '{"image_path": "document.jpg", "question": "Transcribe all the text visible in this image."}')

# Code from screenshot
call_mcp("MEDIA", "understand_image", '{"image_path": "code_snippet.png", "question": "What code is in this screenshot? Output the exact code."}')
```

## Text-to-Speech (TTS)

```
# Basic TTS
call_mcp("MEDIA", "text_to_speech", '{"text": "Hello, this is a test of the text to speech system.", "output_path": "hello.mp3"}')

# Different voice and speed
call_mcp("MEDIA", "text_to_speech", '{"text": "欢迎使用语音合成系统。", "voice": "nova", "speed": 1.2, "output_path": "welcome.mp3"}')
```

### Voice options
- `alloy` — neutral (default)
- `echo` — warm, deeper
- `fable` — expressive, British
- `onyx` — deep, authoritative
- `nova` — warm, friendly
- `shimmer` — clear, upbeat

### Speed
- Range: 0.25 to 4.0
- 1.0 is normal speed

## Speech-to-Text (STT / Whisper)

```
# Basic transcription
call_mcp("MEDIA", "speech_to_text", '{"audio_path": "recording.mp3"}')

# With language hint
call_mcp("MEDIA", "speech_to_text", '{"audio_path": "meeting.mp3", "language": "zh"}')

# Verbose JSON output (with timestamps)
call_mcp("MEDIA", "speech_to_text", '{"audio_path": "interview.mp3", "language": "en", "response_format": "verbose_json"}')
```

### Supported formats
MP3, WAV, M4A, WEBM, MP4, MPGA, OGG — max 25 MB.

### Language codes
`zh` (Chinese), `en` (English), `ja` (Japanese), `ko` (Korean), empty for auto-detect.

## Requirements
- Set `OPENAI_API_KEY` environment variable.
- Optionally set `OPENAI_BASE_URL` for alternative endpoints.
- Model overrides: `MEDIA_IMAGE_MODEL`, `MEDIA_VISION_MODEL`, `MEDIA_TTS_MODEL`, `MEDIA_STT_MODEL`.
