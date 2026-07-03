from __future__ import annotations

import json
from pathlib import Path


async def session_search(query: str, max_results: int = 5) -> str:
    """Search saved conversation histories in this workspace.

    Args:
        query: Case-insensitive text query.
        max_results: Maximum matching excerpts to return.
    """
    needle = query.lower().strip()
    if not needle:
        return "[Error] query cannot be empty"
    workspace = Path(__file__).parents[1]
    histories = workspace / "histories"
    if not histories.is_dir():
        return "[No histories] This workspace has no saved sessions yet."
    matches: list[str] = []
    for path in sorted(histories.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            if needle not in line.lower():
                continue
            try:
                msg = json.loads(line)
                text = str(msg.get("content") or msg.get("reasoning") or msg)
            except Exception:
                text = line
            text = " ".join(text.split())
            if len(text) > 500:
                text = text[:500] + " ..."
            matches.append(f"{path.name}:{lineno}: {text}")
            if len(matches) >= max_results:
                return "\n".join(matches)
    return f"[No matches] {query}"
