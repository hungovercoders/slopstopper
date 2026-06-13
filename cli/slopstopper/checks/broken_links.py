"""Broken-link checks (Playwright wrapper).

Ports the bash reliability:links flow:

  task ss:reliability:links -- https://your-site.example.com

  which is, under the covers:

  BROKEN_LINKS_PAGES=$(python3 .ss/scripts/discover-pages.py
                              broken_links --event=local)
  BROKEN_LINKS_TEST_URL=...
  npx playwright test --config=.ss/playwright.config.js
                      .ss/tests/broken-links.spec.ts
                      --reporter=list[,html]

Subprocess-invokes `npx playwright`. Playwright is Apache-2.0; the
slopstopper-cli wheel ships zero Playwright code. Page discovery uses
the in-CLI slopstopper.discovery module.

Falls back to SMOKE_TEST_URL when BROKEN_LINKS_TEST_URL is unset,
matching the bash flow exactly.

Configuration (.slopstopper.yml — all optional):

    pages:
      broken_links: /,/blog,/about
    reliability:
      coverage:
        pr: changed     # see slopstopper.discovery for the resolution order
        main: sitemap

See .slopstopper.yml.example for the canonical schema and coverage
modes.

Exit codes:
  0 — playwright tests passed
  non-zero — playwright tests failed, or URL/spec missing
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess

from slopstopper import discovery, templates

SPEC_NAME = "broken-links"


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="slopstopper run reliability:broken-links", add_help=False
    )
    p.add_argument("--url", default=None, help="Site URL to scan")
    p.add_argument("--ci", action="store_true", help="CI mode: html reporter, CI=true")
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _npx_available() -> bool:
    return shutil.which("npx") is not None


def _resolve_url(parsed_url: str | None) -> str | None:
    return (
        parsed_url
        or os.environ.get("BROKEN_LINKS_TEST_URL")
        or os.environ.get("SMOKE_TEST_URL")
    )


def _discover_pages() -> str | None:
    """Resolve pages.broken_links via the in-CLI discovery module."""
    try:
        paths = discovery.discover("broken_links", "local")
    except Exception:
        return None
    return ",".join(paths) if paths else None


def _build_env(url: str, ci_mode: bool) -> dict[str, str]:
    env = dict(os.environ)
    env["BROKEN_LINKS_TEST_URL"] = url
    if "BROKEN_LINKS_PAGES" not in env:
        pages = _discover_pages()
        if pages is not None:
            env["BROKEN_LINKS_PAGES"] = pages
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
        print("❌ Error: broken-links target URL is required")
        print("Usage:")
        print("  slopstopper run reliability:broken-links -- --url https://your-site.example.com")
        print("  BROKEN_LINKS_TEST_URL=https://your-site slopstopper run reliability:broken-links")
        return 1

    spec = templates.playwright_spec(SPEC_NAME)
    if not spec.exists():
        print(f"❌ Broken-links spec not found at {spec}")
        return 1

    print(f"🔗 Running broken-link checks against: {url}")
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    result = subprocess.run(cmd, env=env, check=False)
    return result.returncode
