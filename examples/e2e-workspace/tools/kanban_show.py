from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path


async def kanban_show(action: str = "list", task_id: str = "", title: str = "", notes: str = "") -> str:
    """Manage a tiny file-backed kanban board for this workspace.

    Args:
        action: list, add, start, done, block, or show.
        task_id: Task id for show/start/done/block.
        title: Task title for add.
        notes: Optional notes for add or block.
    """
    path = Path(__file__).parents[1] / "kanban.json"
    if path.exists():
        try:
            board = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            board = {"tasks": []}
    else:
        board = {"tasks": []}
    tasks = board.setdefault("tasks", [])

    def save() -> None:
        path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")

    if action == "add":
        if not title.strip():
            return "[Error] title is required for add"
        next_id = str(max([int(t.get("id", "0")) for t in tasks if str(t.get("id", "")).isdigit()] or [0]) + 1)
        tasks.append({"id": next_id, "title": title.strip(), "status": "todo", "notes": notes, "updated_at": datetime.now(UTC).isoformat()})
        save()
        return f"[OK] Added task {next_id}: {title.strip()}"

    if action in ("show", "start", "done", "block"):
        task = next((t for t in tasks if str(t.get("id")) == task_id), None)
        if task is None:
            return f"[Error] Task not found: {task_id}"
        if action == "show":
            return json.dumps(task, ensure_ascii=False, indent=2)
        task["status"] = {"start": "doing", "done": "done", "block": "blocked"}[action]
        if notes:
            task["notes"] = notes
        task["updated_at"] = datetime.now(UTC).isoformat()
        save()
        return f"[OK] Task {task_id} -> {task['status']}"

    groups = {"todo": [], "doing": [], "blocked": [], "done": []}
    for task in tasks:
        groups.setdefault(task.get("status", "todo"), []).append(task)
    lines = []
    for status in ("todo", "doing", "blocked", "done"):
        lines.append(f"## {status}")
        if not groups.get(status):
            lines.append("(empty)")
        for task in groups.get(status, []):
            suffix = f" - {task.get('notes')}" if task.get("notes") else ""
            lines.append(f"- {task.get('id')}: {task.get('title')}{suffix}")
    return "\n".join(lines)
