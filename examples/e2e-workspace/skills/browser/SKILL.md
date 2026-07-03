---
name: browser
description: "Browser automation via Playwright MCP — navigate, screenshot, click, type, scrape, evaluate JS."
---

# Browser Automation (Playwright MCP)

Use the PW MCP server for all browser interactions. **Connections are now pooled — browser state persists across calls!**

## Quick start

Always `list_mcp_tools("PW")` first to see the full tool list (23 tools).

### Core tools:
- `browser_navigate` — open a URL
- `browser_take_screenshot` — save screenshot (use `filename` param!)
- `browser_snapshot` — text-based page structure (best for AI understanding)
- `browser_click` — click elements
- `browser_type` — type into fields
- `browser_evaluate` — run JavaScript
- `browser_wait_for` — wait for text or timeout
- `browser_close` — close the page

## Common patterns

### Open a page and read content
```
call_mcp("PW", "browser_navigate", '{"url": "https://example.com"}')
call_mcp("PW", "browser_snapshot", "{}")    # text page structure
```

### Open a page and screenshot
```
call_mcp("PW", "browser_navigate", '{"url": "https://example.com"}')
call_mcp("PW", "browser_wait_for", '{"time": 2000}')   # wait for render
call_mcp("PW", "browser_take_screenshot", '{"filename": "E:/abs/path/shot.png"}')
```

### Click and interact (multi-step, state persists!)
```
call_mcp("PW", "browser_navigate", '{"url": "https://example.com"}')
call_mcp("PW", "browser_click", '{"element": "Login", "target": "text=Login"}')
call_mcp("PW", "browser_type", '{"element": "email field", "target": "#email", "text": "user@example.com"}')
call_mcp("PW", "browser_type", '{"element": "password field", "target": "#password", "text": "secret"}')
call_mcp("PW", "browser_click", '{"element": "submit button", "target": "button[type=submit]"}')
call_mcp("PW", "browser_snapshot", "{}")     # see the result page
```

### Extract page data
```
call_mcp("PW", "browser_evaluate", '{"function": "() => document.title"}')
call_mcp("PW", "browser_evaluate", '{"function": "() => document.body.innerText"}')
```

## Screenshot rules
- Tool name is `browser_take_screenshot` (NOT `browser_screenshot`)
- Must provide `filename` param with an absolute path ending in `.png`
- Screenshot files can then be analyzed with VISION MCP for visual understanding

## Best practices
- Use `browser_snapshot` for AI to understand page structure (text-based).
- Use `browser_take_screenshot` + VISION MCP for visual analysis (layout, colors, images).
- Call `close_mcp("PW")` when done with a browser session.
- For dynamic pages, use `browser_wait_for` to wait for content to load.

## Requirements
- Node.js must be installed.
- Configure: `MCP_PW_COMMAND="npx"` and `MCP_PW_ARGS='["-y", "@playwright/mcp@latest"]'`.
