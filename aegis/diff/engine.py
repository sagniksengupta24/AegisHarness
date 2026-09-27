"""Diff engine for computing unified diffs, diff preview, and interactive approval."""

import difflib
import sys
from pathlib import Path
from typing import Optional


def compute_unified_diff(
    original_text: str,
    new_text: str,
    file_path: str = "target",
    context_lines: int = 3,
) -> str:
    """Computes a standard unified diff between original and new content."""
    orig_lines = original_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    
    diff_generator = difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=context_lines,
    )
    return "".join(diff_generator)


def colorize_diff(diff_text: str) -> str:
    """Adds ANSI terminal colors to unified diff output."""
    lines = []
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            lines.append(f"\033[1m{line}\033[0m")
        elif line.startswith("+"):
            lines.append(f"\033[32m{line}\033[0m")
        elif line.startswith("-"):
            lines.append(f"\033[31m{line}\033[0m")
        elif line.startswith("@@"):
            lines.append(f"\033[36m{line}\033[0m")
        else:
            lines.append(line)
    return "\n".join(lines)


def request_interactive_approval(
    diff_text: str,
    file_path: str,
    prompt_callback: Optional[callable] = None,
) -> bool:
    """Presents the proposed diff and prompts the user for approval BEFORE writing."""
    colored = colorize_diff(diff_text)
    header = f"\n=== [PROPOSED CHANGE: {file_path}] ===\n"
    sys.stdout.write(header)
    sys.stdout.write(colored + "\n")
    sys.stdout.flush()

    if prompt_callback:
        return prompt_callback(file_path, diff_text)

    try:
        ans = input(f"Apply this change to '{file_path}'? [y/N]: ").strip().lower()
        return ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
