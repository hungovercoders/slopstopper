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

from slopstopper import config, output
from slopstopper.checks import _playwright, _tools

CHECK = _playwright.Check(
    name="e2e",
    spec_name="e2e",
    url_env="E2E_TEST_URL",
    url_fallbacks=(),
    title="## 🧭 E2E Journey Results",
    failure_hint=(
        "A user journey is failing. The failing step is named in the "
        "[Playwright HTML report](playwright-report/index.html) (uploaded as an "
        "artifact in CI); the test title says which start path and which journey."
    ),
    banner="Walking user journeys against: {url}",
    verb="walk",
)
SPEC_NAME = CHECK.spec_name
REPORT_DIR = _playwright.REPORT_DIR
PLAYWRIGHT_JSON = CHECK.playwright_json
REPORT_MD = CHECK.report_md

# Consumed by `slopstopper emit reliability:e2e --target {pr-comment,issue}`.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": CHECK.title,
    "issue_title": "🧭 E2E Journeys Failing on Main Branch",
    "issue_labels": ["e2e-failure", "reliability"],
    "issue_followup": "🔔 E2E journeys failing again in commit",
    "issue_close_comment": "✅ E2E journeys are passing again on `main`. Closing automatically.",
}

DEFAULT_MAX_LINKS = 25

_npx_available = _tools.npx_available


def _parse_args(args: list[str] | None):
    return _playwright.parse_args(CHECK, args)


def _resolve_url(parsed_url: str | None) -> str | None:
    return _playwright.resolve_url(CHECK, parsed_url)


def _max_links() -> int:
    """`e2e.max_links` as a positive int; anything else falls back to the default."""
    raw = config.get("e2e.max_links", DEFAULT_MAX_LINKS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        output.warn(f"e2e.max_links={raw!r} is not a positive integer; using {DEFAULT_MAX_LINKS}")
        return DEFAULT_MAX_LINKS
    return value


def _build_env(url: str, ci_mode: bool) -> dict[str, str]:
    env = _playwright.base_env(CHECK, url, ci_mode)
    env.setdefault("E2E_PAGES", str(config.get("pages.e2e", "/")))
    env.setdefault("E2E_MAX_LINKS", str(_max_links()))
    return env


def _build_cmd(ci_mode: bool) -> list[str]:
    return _playwright.build_cmd(SPEC_NAME, ci_mode)


def run(args: list[str] | None = None) -> int:
    return _playwright.run_check(CHECK, args, npx_available=_npx_available, build_env=_build_env)
