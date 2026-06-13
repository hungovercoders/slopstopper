"""Smoke tests against a live URL (Playwright wrapper).

Implements the reliability:smoke flow:

  slopstopper run reliability:smoke -- --url https://your-site.example.com

  which is, under the covers:

  SMOKE_TEST_URL=...
  SMOKE_OG_IMAGE_PATH=<smoke.og_image_path from .slopstopper.yml>
  SMOKE_PAGES=<pages.smoke from .slopstopper.yml>
  npx playwright test --config=<resolved playwright config>
                      <resolved smoke spec>
                      --reporter=list[,html]

Subprocess-invokes `npx playwright` — Playwright is Apache-2.0; the
slopstopper-cli wheel ships zero Playwright code. The test specs and
Playwright config are bundled in the wheel; adopters can override by
writing same-named files under .ss/ (see slopstopper.templates).

Configuration (.slopstopper.yml — all optional):

    pages:
      smoke: /,/blog,/about       # which paths to smoke-test
    smoke:
      og_image_path: /og-image.png  # '' to skip the og-image assertion

See .slopstopper.yml.example for the canonical schema.

Exit codes:
  0 — playwright tests passed
  non-zero — playwright tests failed, or URL/spec missing
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess

from slopstopper import config, templates

SPEC_NAME = "smoke"


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
        f"--config={templates.playwright_config()}",
        str(templates.playwright_spec(SPEC_NAME)),
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

    print(f"🔍 Running smoke tests against: {url}")
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    result = subprocess.run(cmd, env=env, check=False)
    return result.returncode
