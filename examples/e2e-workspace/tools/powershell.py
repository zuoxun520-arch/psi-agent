from __future__ import annotations

import shutil
from pathlib import Path

import anyio


def _find_powershell() -> str:
    found = shutil.which("pwsh") or shutil.which("powershell")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    return "powershell"


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8", "mbcs"):
        try:
            return raw.decode(encoding)
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace")


async def powershell(command: str, cwd: str = "", timeout_seconds: int = 30) -> str:
    """Run a PowerShell command and return stdout plus stderr.

    Args:
        command: PowerShell command to execute.
        cwd: Working directory. Defaults to the workspace root.
        timeout_seconds: Maximum runtime in seconds.
    """
    workdir = cwd or str(Path(__file__).parents[1])
    args = [_find_powershell(), "-NoProfile", "-NonInteractive", "-OutputFormat", "Text", "-Command", command]
    try:
        with anyio.fail_after(timeout_seconds):
            result = await anyio.run_process(args, cwd=workdir, check=False)
    except TimeoutError:
        return f"[Error] Command timed out after {timeout_seconds}s"
    text = _decode(result.stdout).strip()
    err = _decode(result.stderr).strip()
    if err:
        text = (text + "\n[stderr]\n" + err).strip()
    if result.returncode != 0:
        text += f"\n[Exit code: {result.returncode}]"
    return text or "(no output)"
