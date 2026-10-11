"""Probes for, and one-line calls to, the external tools checks shell out to.

`npx` backs both the Playwright checks (smoke, e2e, accessibility,
broken-links) and Lighthouse CI (cwv); `git` tells docs-accuracy and
complexity which files the repo owns. Neither belongs to one check, so
they live here rather than in a check's helper module.
"""

from __future__ import annotations

import shutil
import subprocess
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
