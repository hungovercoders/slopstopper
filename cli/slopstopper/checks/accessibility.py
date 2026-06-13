"""Accessibility audit (Playwright + axe-core wrapper).

Ports the bash reliability:accessibility flow:

  task ss:reliability:accessibility -- https://your-site.example.com

  which is, under the covers:

  ACCESSIBILITY_PAGES=$(python3 .ss/scripts/discover-pages.py
                                accessibility --event=local)
  ACCESSIBILITY_TEST_URL=...
  npx playwright test --config=.ss/playwright.config.js
                      .ss/tests/accessibility.spec.ts
                      --reporter=list[,html]

Subprocess-invokes `npx playwright`. Playwright is Apache-2.0, axe-core
is MPL-2.0; the slopstopper-cli wheel ships zero code from either —
both bind in via the adopter's node_modules. Discover-pages.py is
still an adopter-vendored Python script today (subprocess-invoked
here for parity); lifting it into the package is a follow-up.

Falls back to SMOKE_TEST_URL when ACCESSIBILITY_TEST_URL is unset,
matching the bash flow exactly.

Exit codes:
  0 — playwright tests passed
  non-zero — playwright tests failed, or URL/spec missing
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from slopstopper import discovery

SPEC_PATH = Path(".ss/tests/accessibility.spec.ts")
PLAYWRIGHT_CONFIG = Path(".ss/playwright.config.js")


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="slopstopper run reliability:accessibility", add_help=False
    )
    p.add_argument("--url", default=None, help="Site URL to audit")
    p.add_argument("--ci", action="store_true", help="CI mode: html reporter, CI=true")
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _npx_available() -> bool:
    return shutil.which("npx") is not None


def _resolve_url(parsed_url: str | None) -> str | None:
    return (
        parsed_url
        or os.environ.get("ACCESSIBILITY_TEST_URL")
        or os.environ.get("SMOKE_TEST_URL")
    )


def _discover_pages() -> str | None:
    """Resolve pages.accessibility from .slopstopper.yml via the in-CLI
    discovery module. Returns None on internal failure so the spec falls
    back to its built-in default.
    """
    try:
        paths = discovery.discover("accessibility", "local")
    except Exception:
        return None
    return ",".join(paths) if paths else None


def _build_env(url: str, ci_mode: bool) -> dict[str, str]:
    env = dict(os.environ)
    env["ACCESSIBILITY_TEST_URL"] = url
    if "ACCESSIBILITY_PAGES" not in env:
        pages = _discover_pages()
        if pages is not None:
            env["ACCESSIBILITY_PAGES"] = pages
    if ci_mode:
        env["CI"] = "true"
    return env


def _build_cmd(ci_mode: bool) -> list[str]:
    reporter = "list,html" if ci_mode else "list"
    return [
        "npx", "playwright", "test",
        f"--config={PLAYWRIGHT_CONFIG}",
        str(SPEC_PATH),
        f"--reporter={reporter}",
    ]


def run(args: list[str] | None = None) -> int:
    if not _npx_available():
        print("❌ npx is not available — install Node.js to run Playwright tests")
        return 1

    parsed = _parse_args(args)
    url = _resolve_url(parsed.url)
    if not url:
        print("❌ Error: accessibility target URL is required")
        print("Usage:")
        print("  slopstopper run reliability:accessibility -- --url https://your-site.example.com")
        print("  ACCESSIBILITY_TEST_URL=https://your-site slopstopper run reliability:accessibility")
        return 1

    if not SPEC_PATH.exists():
        print(f"❌ Accessibility spec not found at {SPEC_PATH}")
        print("   The spec is vendored under .ss/tests/ by the installer.")
        return 1

    print(f"♿ Running accessibility audit against: {url}")
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    result = subprocess.run(cmd, env=env, check=False)
    return result.returncode
