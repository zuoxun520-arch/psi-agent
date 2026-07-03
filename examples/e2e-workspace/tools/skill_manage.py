from __future__ import annotations

import re
from datetime import datetime, UTC
from pathlib import Path


def _skills_dir() -> Path:
    return Path(__file__).parents[1] / "skills"


def _valid(name: str) -> str:
    if not name or not name.strip():
        return "skill_name is required"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return "skill_name may contain only letters, digits, underscores, and hyphens"
    return ""


def _frontmatter(raw: str) -> dict[str, str]:
    if not raw.startswith("---"):
        return {}
    end = raw.find("\n---", 3)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in raw[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip().strip("'\"")
    return result


async def skill_manage(action: str = "list", skill_name: str = "", content: str = "", description: str = "", category: str = "general") -> str:
    """List, view, create, or patch skills in this workspace.

    Args:
        action: list, view, create, or patch.
        skill_name: Skill directory name for view/create/patch.
        content: SKILL.md body for create/patch.
        description: Short description for create.
        category: Category for create.
    """
    skills = _skills_dir()
    skills.mkdir(parents=True, exist_ok=True)

    if action == "list":
        rows: list[str] = []
        for path in sorted(skills.iterdir()):
            if not path.is_dir() or path.name.startswith("."):
                continue
            skill_md = path / "SKILL.md"
            if not skill_md.exists():
                continue
            fm = _frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
            rows.append(f"- {fm.get('name') or path.name} ({fm.get('category') or 'general'}): {fm.get('description') or '(no description)'}")
        return "Skills:\n" + "\n".join(rows) if rows else "No skills found."

    err = _valid(skill_name)
    if err:
        return f"[Error] {err}"
    skill_md = skills / skill_name / "SKILL.md"

    if action == "view":
        if not skill_md.exists():
            return f"[Error] Skill not found: {skill_name}"
        return skill_md.read_text(encoding="utf-8", errors="replace")

    if action == "create":
        if skill_md.exists():
            return f"[Error] Skill already exists: {skill_name}"
        skill_md.parent.mkdir(parents=True, exist_ok=False)
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        text = "\n".join([
            "---",
            f"name: {skill_name}",
            f"description: {description or '(no description)'}",
            f"category: {category or 'general'}",
            "source: local",
            f"created_at: {now}",
            "---",
            "",
            content or "# Instructions\n\nDescribe when and how to use this skill.",
        ])
        skill_md.write_text(text, encoding="utf-8")
        return f"[OK] Created skill: {skill_name}"

    if action == "patch":
        if not skill_md.exists():
            return f"[Error] Skill not found: {skill_name}"
        raw = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = _frontmatter(raw)
        fm["updated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = ["---", *[f"{k}: {v}" for k, v in fm.items()], "---", "", content]
        skill_md.write_text("\n".join(lines), encoding="utf-8")
        return f"[OK] Patched skill: {skill_name}"

    return "[Error] action must be one of: list, view, create, patch"
