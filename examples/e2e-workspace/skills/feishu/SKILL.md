---
name: feishu
description: "Feishu/Lark messaging — send text, interactive cards, images, and files via webhook or API."
---

# Feishu / Lark Messaging (FEISHU MCP)

Use the FEISHU MCP server to send messages, cards, images, and files to Feishu.

## Quick start

```
# Discover tools
call_mcp("FEISHU", "list_mcp_tools", "")

# Tools: feishu_send_text, feishu_send_card, feishu_upload_image,
#         feishu_send_image, feishu_send_file
```

## Authentication

Two modes:

1. **Webhook mode** (simplest) — set `FEISHU_WEBHOOK_URL` env var.
   Get a webhook URL from a Feishu group: Group Settings → Bots → Add Bot → Custom Bot → Copy Webhook URL.

2. **API mode** (full-featured) — set `FEISHU_APP_ID` and `FEISHU_APP_SECRET`.
   Create an app at https://open.feishu.cn/app.

Webhook mode supports text and cards. API mode adds image/file upload.

## Send a text message

```
call_mcp("FEISHU", "feishu_send_text", '{"content": "Task completed: report generated at reports/daily.md"}')
```

### Feishu Markdown in text
```
call_mcp("FEISHU", "feishu_send_text", '{"content": "**Bold title**\\n- Item 1\\n- Item 2\\n<at id=all> everyone"}')
```

## Send an interactive card

```
call_mcp("FEISHU", "feishu_send_card", '{"title": "Build Status", "content": "✅ All tests passed\\n📦 Version: v2.1.0\\n⏱ Duration: 3m 42s", "header_color": "green"}')
```

### Card header colors
`blue` (default), `green`, `red`, `yellow`, `purple`, `turquoise`, `wathet`, `carmine`, `indigo`, `orange`

### Card with buttons
```
call_mcp("FEISHU", "feishu_send_card", '{"title": "Deploy?", "content": "Deploy v2.1.0 to production?", "elements_json": "[{\\"tag\\": \\"button\\", \\"text\\": {\\"tag\\": \\"plain_text\\", \\"content\\": \\"Approve\\"}, \\"type\\": \\"primary\\"}, {\\"tag\\": \\"button\\", \\"text\\": {\\"tag\\": \\"plain_text\\", \\"content\\": \\"Reject\\"}, \\"type\\": \\"danger\\"}]", "header_color": "red"}')
```

## Upload and send an image

```
# Step 1: Upload image (requires API mode)
call_mcp("FEISHU", "feishu_upload_image", '{"image_path": "chart.png"}')
# Returns: [OK] Image uploaded. image_key: img_xxxxx

# Step 2: Send the image
call_mcp("FEISHU", "feishu_send_image", '{"image_key_or_url": "img_xxxxx"}')
```

## Send a file

```
call_mcp("FEISHU", "feishu_send_file", '{"file_path": "reports/monthly.pdf"}')
```

## Common workflows

### Build notification
```
# After CI passes
call_mcp("FEISHU", "feishu_send_card", '{"title": "CI Passed", "content": "Branch: main\\nCommit: abc1234\\nCoverage: 92%", "header_color": "green"}')
```

### Daily report
```
call_mcp("FEISHU", "feishu_send_text", '{"content": "📊 Daily Report\\n- Tasks completed: 12\\n- PRs merged: 3\\n- Issues opened: 1"}')
```

### Alert notification
```
call_mcp("FEISHU", "feishu_send_card", '{"title": "⚠ Alert", "content": "CPU usage exceeded 90% on prod-server-01\\nTime: 14:32 UTC", "header_color": "red"}')
```

## Requirements
- For webhook mode: `FEISHU_WEBHOOK_URL` env var.
- For API mode: `FEISHU_APP_ID` + `FEISHU_APP_SECRET` env vars.
- Configure MCP: `MCP_FEISHU_COMMAND="uv"` and `MCP_FEISHU_ARGS='["run", "python", "e2e-workspace/mcp_servers/feishu_server.py"]'`.
