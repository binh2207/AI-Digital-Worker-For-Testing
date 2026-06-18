"""
Claude CLI wrapper — calls `claude --print` as a subprocess.
Uses a neutral cwd (home dir) to avoid loading project context/CLAUDE.md,
which was the root cause of >300s timeouts.
"""
import subprocess
from pathlib import Path
from config import CLAUDE_CMD

_NEUTRAL_CWD = str(Path.home())


def call_claude(prompt: str, max_tokens: int = 8096) -> str | None:
    """Run claude --print with the given prompt. Returns text output or None on failure."""
    try:
        result = subprocess.run(
            [CLAUDE_CMD, "--print", "--output-format", "text"],
            input=prompt,
            capture_output=True, text=True, encoding="utf-8",
            timeout=600, cwd=_NEUTRAL_CWD,
        )
        output = result.stdout.strip()
        if not output:
            print(f"[claude_client] No output (exit={result.returncode}). stderr: {result.stderr[:300]}")
        return output or None
    except subprocess.TimeoutExpired:
        print("[claude_client] Claude CLI timed out after 600s.")
        return None
    except Exception as exc:
        print(f"[claude_client] Error calling Claude CLI: {exc}")
        return None
