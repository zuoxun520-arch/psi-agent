from __future__ import annotations

import os
import shutil

import anyio


async def _find_bash() -> str:
    found = shutil.which("bash")
    if found:
        return found
    if os.name == "nt":
        for candidate in (
            "C:/Program Files/Git/bin/bash.exe",
            "C:/Program Files/Git/usr/bin/bash.exe",
            "D:/Program Files/Git/bin/bash.exe",
            "D:/Program Files/Git/usr/bin/bash.exe",
        ):
            if await anyio.Path(candidate).is_file():
                return candidate
    return ""


async def bash(command: str, timeout_seconds: int = 30) -> str:
    """Run a shell command through bash and return stdout plus stderr.

    Args:
        command: Command to execute.
        timeout_seconds: Maximum runtime in seconds.
    """
    bash_path = await _find_bash()
    if not bash_path:
        return "[Error] bash executable not found. Install Git Bash, WSL, or bash."
    try:
        with anyio.fail_after(timeout_seconds):
            result = await anyio.run_process([bash_path, "-lc", command], check=False)
    except TimeoutError:
        return f"[Error] Command timed out after {timeout_seconds}s"
    out = result.stdout.decode(errors="replace")
    err = result.stderr.decode(errors="replace")
    text = (out + err).rstrip()
    if result.returncode != 0:
        text += f"\n[Exit code: {result.returncode}]"
    return text or "(no output)"
