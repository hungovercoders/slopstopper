"""End-to-end user journeys against a live URL (Playwright wrapper).

Implements the reliability:e2e flow:

  slopstopper run reliability:e2e -- --url https://your-site.example.com

  which is, under the covers:

  E2E_TEST_URL=...
  E2E_PAGES=<pages.e2e from .slopstopper.yml>
  E2E_MAX_LINKS=<e2e.max_links from .slopstopper.yml>
  npx playwright test --config=<resolved playwright config>
                      <resolved e2e spec>
                      --reporter=list[,html],json

Where smoke asks "does each page render", this asks "can a visitor get
around": from each start path the bundled spec clicks every same-origin
link in the primary <nav>, asserts the destination answers, has a
heading and still carries the nav; follows every in-page anchor to an
element that exists; opens and closes every <details>; and checks the
browser's back button returns to where the journey began. Nothing in it
names a selector or a page of this site, so it runs unchanged on any
HTML site. Journeys that are specific to one site go in an ejected copy
(`slopstopper templates eject tests/e2e.spec.ts`).

Subprocess-invokes `npx playwright` — Playwright is Apache-2.0; the
slopstopper-cli wheel ships zero Playwright code. The spec and the
Playwright config are bundled in the wheel; adopters can override by
writing same-named files under .ss/ (see slopstopper.templates).

Configuration (.slopstopper.yml — all optional):

    pages:
      e2e: /,/pricing            # start paths for the journeys (default /)
    e2e:
      max_links: 25              # nav links followed per start path

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

SPEC_NAME = "e2e"
REPORT_DIR = Path(".ss/reports/reliability")
# Playwright's JSON reporter output: whether the tests ran at all (see
# `_contract.playwright_ran`) — its exit code alone can't say.
PLAYWRIGHT_JSON = REPORT_DIR / "e2e-results.json"
REPORT_MD = REPORT_DIR / "e2e-report.md"

# Consumed by `slopstopper emit reliability:e2e --target {pr-comment,issue}`.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "## 🧭 E2E Journey Results",
    "issue_title": "🧭 E2E Journeys Failing on Main Branch",
    "issue_labels": ["e2e-failure", "reliability"],
    "issue_followup": "🔔 E2E journeys failing again in commit",
    "issue_close_comment": "✅ E2E journeys are passing again on `main`. Closing automatically.",
}


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run reliability:e2e", add_help=False)
    p.add_argument(
        "url_positional",
        nargs="?",
        default=None,
        help="Site URL to walk (alternative to --url; e.g. http://localhost:8080)",
    )
    p.add_argument("--url", default=None, help="Site URL to walk (else $E2E_TEST_URL)")
    p.add_argument("--ci", action="store_true", help="CI mode: html reporter, CI=true")
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


_npx_available = _tools.npx_available


def _resolve_url(parsed_url: str | None) -> str | None:
    return parsed_url or os.environ.get("E2E_TEST_URL")


def _build_env(url: str, ci_mode: bool) -> dict[str, str]:
    env = dict(os.environ)
    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(Path.cwd() / PLAYWRIGHT_JSON)
    env["E2E_TEST_URL"] = url
    env.setdefault("E2E_PAGES", str(config.get("pages.e2e", "/")))
    env.setdefault("E2E_MAX_LINKS", str(config.get("e2e.max_links", 25)))
    if ci_mode:
        env["CI"] = "true"
    return env


def _ensure_playwright_assets_ejected() -> None:
    _playwright.ensure_assets_ejected(SPEC_NAME)


def _build_cmd(ci_mode: bool) -> list[str]:
    return _playwright.build_cmd(SPEC_NAME, ci_mode)


def _write_report(exit_code: int, url: str) -> None:
    _playwright.write_summary(
        REPORT_DIR, REPORT_MD, "## 🧭 E2E Journey Results", exit_code, url,
        "A user journey is failing. The failing step is named in the "
        "[Playwright HTML report](playwright-report/index.html) (uploaded as an "
        "artifact in CI); the test title says which start path and which journey.",
    )


def run(args: list[str] | None = None) -> int:
    if not _npx_available():
        output.error("npx is not available — install Node.js to run Playwright tests")
        return 2

    parsed = _parse_args(args)
    url = _resolve_url(parsed.url_positional or parsed.url)
    if not url:
        output.error("e2e target URL is required")
        output._emit("Usage:")
        output._emit("  slopstopper run reliability:e2e -- --url https://your-site.example.com")
        output._emit("  E2E_TEST_URL=https://your-site slopstopper run reliability:e2e")
        return 2

    output.running(f"Walking user journeys against: {url}")
    _ensure_playwright_assets_ejected()
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PLAYWRIGHT_JSON.unlink(missing_ok=True)
    result = subprocess.run(cmd, env=env, check=False)
    _write_report(result.returncode, url)
    # Playwright exits 1 both when tests failed (a verdict on the site) and
    # when they never ran (bad config, no browser): the JSON report tells
    # the two apart.
    return runner_exit(result.returncode, ran=playwright_ran(PLAYWRIGHT_JSON))
