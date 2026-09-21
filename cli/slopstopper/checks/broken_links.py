"""Broken-link checks (Playwright wrapper).

Ports the bash reliability:broken-links flow:

  task ss:reliability:broken-links -- https://your-site.example.com

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
  1 — playwright tests ran and failed (report still written)
  2 — npx (Node.js) not available, the URL is missing, the bundled
      spec could not be found, or Playwright exited with any other
      non-zero code (the suite didn't run to a verdict).
      Playwright exiting 1 without running the tests (a config error,
      no tests found, the browser failing to launch) is 2 as well
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from slopstopper import discovery, output, templates
from slopstopper.checks import _playwright, _report
from slopstopper.checks._contract import playwright_ran, runner_exit

SPEC_NAME = "broken-links"
REPORT_DIR = Path(".ss/reports/reliability")
# Playwright's JSON reporter output: whether the tests ran at all (see
# `_contract.playwright_ran`) — its exit code alone can't say.
PLAYWRIGHT_JSON = REPORT_DIR / "broken-links-results.json"
REPORT_MD = REPORT_DIR / "broken-links-report.md"

# Consumed by `slopstopper emit reliability:broken-links --target {pr-comment,issue}`.
# New issue surface — previously this check never opened main-branch issues
# (the workflow built a PR comment manually but never escalated to an issue).
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "## 🔗 Broken Links Report",
    "issue_title": "🔗 Broken Links on Main Branch",
    "issue_labels": ["broken-links", "reliability"],
    "issue_followup": "🔔 Broken links detected again in commit",
    "issue_close_comment": "✅ Broken-link check is now passing on `main`. Closing automatically.",
}


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="slopstopper run reliability:broken-links", add_help=False
    )
    p.add_argument(
        "url_positional",
        nargs="?",
        default=None,
        help="Site URL to scan (alternative to --url; e.g. http://localhost:8080)",
    )
    p.add_argument("--url", default=None, help="Site URL to scan")
    p.add_argument("--ci", action="store_true", help="CI mode: html reporter, CI=true")
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


_npx_available = _playwright.npx_available


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
    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(Path.cwd() / PLAYWRIGHT_JSON)
    env["BROKEN_LINKS_TEST_URL"] = url
    if "BROKEN_LINKS_PAGES" not in env:
        pages = _discover_pages()
        if pages is not None:
            env["BROKEN_LINKS_PAGES"] = pages
    if ci_mode:
        env["CI"] = "true"
    return env


def _ensure_playwright_assets_ejected() -> None:
    _playwright.ensure_assets_ejected(SPEC_NAME)


def _build_cmd(ci_mode: bool) -> list[str]:
    return _playwright.build_cmd(SPEC_NAME, ci_mode)


_gha_run_url = _report.gha_run_url


def _write_report(exit_code: int, url: str) -> None:
    _playwright.write_summary(
        REPORT_DIR, REPORT_MD, '## 🔗 Broken Links Report', exit_code, url,
        'Broken links detected. The [Playwright HTML report](playwright-report/index.html) (uploaded as an artifact in CI) lists each failing link and its source page.',
    )


def run(args: list[str] | None = None) -> int:
    if not _npx_available():
        output.error("npx is not available — install Node.js to run Playwright tests")
        return 2

    parsed = _parse_args(args)
    url = _resolve_url(parsed.url_positional or parsed.url)
    if not url:
        output.error("broken-links target URL is required")
        output._emit("Usage:")
        output._emit("  slopstopper run reliability:broken-links -- --url https://your-site.example.com")
        output._emit("  BROKEN_LINKS_TEST_URL=https://your-site slopstopper run reliability:broken-links")
        return 2

    _ensure_playwright_assets_ejected()
    spec = templates.playwright_spec(SPEC_NAME)
    if not spec.exists():
        output.error(f"Broken-links spec not found at {spec}")
        return 2

    output.status("🔗", f"Running broken-link checks against: {url}")
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PLAYWRIGHT_JSON.unlink(missing_ok=True)
    result = subprocess.run(cmd, env=env, check=False)
    _write_report(result.returncode, url)
    # Playwright's own exit code is kept in the report. It exits 1 both when
    # tests failed (a verdict on the site) and when they never ran (bad
    # config, no browser): the JSON report tells the two apart.
    return runner_exit(result.returncode, ran=playwright_ran(PLAYWRIGHT_JSON))
