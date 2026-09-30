"""Probes for the external tools checks shell out to.

`npx` backs both the Playwright checks (smoke, accessibility,
broken-links) and Lighthouse CI (cwv); neither owns it, so it lives here
rather than in either one's helper module.
"""

from __future__ import annotations

import shutil


def npx_available() -> bool:
    return shutil.which("npx") is not None
