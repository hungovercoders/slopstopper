"""Smoke tests against a live URL (Playwright wrapper).

Ports the bash reliability:smoke flow:

  task ss:reliability:smoke -- https://your-site.example.com

  which is, under the covers:

  SMOKE_TEST_URL=...
  SMOKE_OG_IMAGE_PATH=$(python3 load_config.py smoke.og_image_path /og-image.png)
  SMOKE_PAGES=$(python3 load_config.py pages.smoke /)
  npx playwright test --config=.ss/playwright.config.js
                      .ss/tests/smoke.spec.ts
                      --reporter=list[,html]

Subprocess-invokes `npx playwright` — Playwright is Apache-2.0; the
slopstopper-cli wheel ships zero Playwright code. The test specs at
.ss/tests/smoke.spec.ts and the Playwright config at
.ss/playwright.config.js are still adopter-vendored today (lifting them
into package data is a separate follow-up; see plan).

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

from slopstopper import config

SPEC_PATH = Path(".ss/tests/smoke.spec.ts")
PLAYWRIGHT_CONFIG = Path(".ss/playwright.config.js")


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run reliability:smoke", add_help=False)
    p.add_argument("--url", default=None, help="Site URL to smoke-test (else $SMOKE_TEST_URL)")
    p.add_argument("--ci", action="store_true", help="CI mode: html reporter, CI=true")
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _npx_available() -> bool:
    return shutil.which("npx") is not None


def _resolve_url(parsed_url: str | None) -> str | None:
    return parsed_url or os.environ.get("SMOKE_TEST_URL")


def _build_env(url: str, ci_mode: bool) -> dict[str, str]:
    env = dict(os.environ)
    env["SMOKE_TEST_URL"] = url
    env.setdefault("SMOKE_OG_IMAGE_PATH", str(config.get("smoke.og_image_path", "/og-image.png")))
    env.setdefault("SMOKE_PAGES", str(config.get("pages.smoke", "/")))
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
        print("❌ Error: smoke target URL is required")
        print("Usage:")
        print("  slopstopper run reliability:smoke -- --url https://your-site.example.com")
        print("  SMOKE_TEST_URL=https://your-site slopstopper run reliability:smoke")
        return 1

    if not SPEC_PATH.exists():
        print(f"❌ Smoke spec not found at {SPEC_PATH}")
        print("   The spec is vendored under .ss/tests/ by the installer.")
        return 1

    print(f"🔍 Running smoke tests against: {url}")
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    result = subprocess.run(cmd, env=env, check=False)
    return result.returncode
