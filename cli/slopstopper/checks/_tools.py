"""Probes for, and one-line calls to, the external tools checks shell out to.

`npx` backs both the Playwright checks (smoke, e2e, accessibility,
broken-links) and Lighthouse CI (cwv); `git` tells docs-accuracy and
complexity which files the repo owns; Semgrep and ZAP are run with their
stderr teed so a scan that dies leaves its last lines in the report. None
belongs to one check, so they live here rather than in a check's module.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections import deque
from functools import lru_cache


@lru_cache(maxsize=None)
def git_stdout(cwd: str, *args: str) -> str | None:
    """stdout of `git <args>` in `cwd`, or None when git fails or is absent.

    Cached per (cwd, args) for the life of the process: a check asks the
    same question many times in one run. Pass an absolute `cwd`, so two
    runs in different directories never share an answer.
    """
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def npx_available() -> bool:
    return shutil.which("npx") is not None


def run_tailing_stderr(cmd: list[str], tail_lines: int) -> tuple[int, list[str]]:
    """Run `cmd`; return its exit code and the last non-blank lines of its stderr.

    stderr is echoed live, so the terminal shows the tool's progress, and
    the tail is kept for the report. stdout is left attached. A command
    that cannot start returns 127 with the OS error as its one line, as a
    shell would.
    """
    try:
        # why: `errors=` needs Python 3.6+; the CLI requires >=3.11.
        # nosemgrep: python.lang.compatibility.python36.python36-compatibility-Popen1
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, errors="replace")
    except OSError as exc:
        return 127, [str(exc)]
    tail: deque[str] = deque(maxlen=tail_lines)
    for line in proc.stderr:
        sys.stderr.write(line)
        if line.strip():
            tail.append(line.rstrip())
    return proc.wait(), list(tail)
