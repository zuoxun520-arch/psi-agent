---
name: _universal
description: "Universal working discipline for every task (always loaded first)."
---

# Universal working discipline

Applies to every task regardless of domain.

## MCP First
- Every complex capability goes through MCP. Before using any MCP service, call `list_mcp_tools("<PREFIX>")` to see what's available.
- Configure MCP servers via environment variables (see `.env.example`).
- Each `call_mcp` creates a fresh connection — batch related work.

## Orientation
- Take a quick inventory of the workspace before deep reasoning.
- Read files before editing them. Verify every change.
- Match the output format exactly to what the user expects.

## Shell hygiene
- Use `bash` for Unix commands, `powershell` for Windows.
- Probe for missing tools up front and fall back.
- For large files (>20 lines), base64-encode and decode in place: `printf '%s' '<base64>' | base64 -d > /path/out`.
- Do not use heredoc (`cat <<'EOF'`) in bash — a mis-sent newline hangs the session.

## Verify before declaring done
- Run the smallest useful check after each change.
- Test with real inputs, not assumptions.
- Check file existence, exit codes, and stdout.
- Stop when enough is enough — don't over-verify.

## Budget
- Commit to an approach early. Reserve budget for writing and debugging.
- Don't let setup eat the budget. Chain install commands with `&& echo DONE`.
