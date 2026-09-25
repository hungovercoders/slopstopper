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

from slopstopper import config, output
from slopstopper.checks import _playwright, _tools
from slopstopper.checks._contract import playwright_ran, runner_exit

SPEC_NAME = "smoke"
REPORT_DIR = Path(".ss/reports/reliability")
# Playwright's JSON reporter output: whether the tests ran at all (see
# `_contract.playwright_ran`) — its exit code alone can't say.
PLAYWRIGHT_JSON = REPORT_DIR / "smoke-results.json"
REPORT_MD = REPORT_DIR / "smoke-report.md"

# Consumed by `slopstopper emit reliability:smoke --target {pr-comment,issue}`.
# Issue title + label match the strings the legacy workflow used in raw
# `gh issue create` so existing open issues continue to dedup post-migration.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "## Smoke Test Results",
    "issue_title": "❌ Smoke Tests Failing",
    "issue_labels": ["smoke-test-failure", "reliability"],
    "issue_followup": "🔔 Smoke tests failing again in commit",
    "issue_close_comment": "✅ Smoke tests are now passing on `main`. Closing automatically.",
}


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run reliability:smoke", add_help=False)
    p.add_argument(
        "url_positional",
        nargs="?",
        default=None,
        help="Site URL to smoke-test (alternative to --url; e.g. http://localhost:8080)",
    )
    p.add_argument("--url", default=None, help="Site URL to smoke-test (else $SMOKE_TEST_URL)")
    p.add_argument("--ci", action="store_true", help="CI mode: html reporter, CI=true")
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


_npx_available = _tools.npx_available


def _resolve_url(parsed_url: str | None) -> str | None:
    return parsed_url or os.environ.get("SMOKE_TEST_URL")


def _build_env(url: str, ci_mode: bool) -> dict[str, str]:
    env = dict(os.environ)
    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(Path.cwd() / PLAYWRIGHT_JSON)
    env["SMOKE_TEST_URL"] = url
    env.setdefault("SMOKE_OG_IMAGE_PATH", str(config.get("smoke.og_image_path", "/og-image.png")))
    env.setdefault("SMOKE_PAGES", str(config.get("pages.smoke", "/")))
    if ci_mode:
        env["CI"] = "true"
    return env


def _ensure_playwright_assets_ejected() -> None:
    _playwright.ensure_assets_ejected(SPEC_NAME)


def _build_cmd(ci_mode: bool) -> list[str]:
    return _playwright.build_cmd(SPEC_NAME, ci_mode)




def _write_report(exit_code: int, url: str) -> None:
    _playwright.write_summary(
        REPORT_DIR, REPORT_MD, '## Smoke Test Results', exit_code, url,
        'The smoke tests are failing. Investigate the failing assertion in the [Playwright HTML report](playwright-report/index.html) (uploaded as an artifact in CI).',
    )


def run(args: list[str] | None = None) -> int:
    if not _npx_available():
        output.error("npx is not available — install Node.js to run Playwright tests")
        return 2

    parsed = _parse_args(args)
    url = _resolve_url(parsed.url_positional or parsed.url)
    if not url:
        output.error("smoke target URL is required")
        output._emit("Usage:")
        output._emit("  slopstopper run reliability:smoke -- --url https://your-site.example.com")
        output._emit("  SMOKE_TEST_URL=https://your-site slopstopper run reliability:smoke")
        return 2

    output.running(f"Running smoke tests against: {url}")
    _ensure_playwright_assets_ejected()
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
