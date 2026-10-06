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

from slopstopper import discovery  # noqa: F401 — tests patch `broken_links.discovery.discover`
from slopstopper.checks import _playwright, _tools

CHECK = _playwright.Check(
    name="broken-links",
    spec_name="broken-links",
    url_env="BROKEN_LINKS_TEST_URL",
    url_fallbacks=("SMOKE_TEST_URL",),
    title="## 🔗 Broken Links Report",
    failure_hint=(
        "Broken links detected. The [Playwright HTML report](playwright-report/index.html) "
        "(uploaded as an artifact in CI) lists each failing link and its source page."
    ),
    banner="Running broken-link checks against: {url}",
    banner_icon="🔗",
    verb="scan",
)
SPEC_NAME = CHECK.spec_name
REPORT_DIR = _playwright.REPORT_DIR
PLAYWRIGHT_JSON = CHECK.playwright_json
REPORT_MD = CHECK.report_md

# Consumed by `slopstopper emit reliability:broken-links --target {pr-comment,issue}`.
# New issue surface — previously this check never opened main-branch issues
# (the workflow built a PR comment manually but never escalated to an issue).
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": CHECK.title,
    "issue_title": "🔗 Broken Links on Main Branch",
    "issue_labels": ["broken-links", "reliability"],
    "issue_followup": "🔔 Broken links detected again in commit",
    "issue_close_comment": "✅ Broken-link check is now passing on `main`. Closing automatically.",
}

_npx_available = _tools.npx_available


def _parse_args(args: list[str] | None):
    return _playwright.parse_args(CHECK, args)


def _resolve_url(parsed_url: str | None) -> str | None:
    return _playwright.resolve_url(CHECK, parsed_url)


def _discover_pages() -> str | None:
    """Resolve pages.broken_links (or reliability.coverage.*) for the spec."""
    return _playwright.discover_pages("broken_links")


def _build_env(url: str, ci_mode: bool) -> dict[str, str]:
    env = _playwright.base_env(CHECK, url, ci_mode)
    if "BROKEN_LINKS_PAGES" not in env:
        pages = _discover_pages()
        if pages is not None:
            env["BROKEN_LINKS_PAGES"] = pages
    return env


def _build_cmd(ci_mode: bool) -> list[str]:
    return _playwright.build_cmd(SPEC_NAME, ci_mode)


def run(args: list[str] | None = None) -> int:
    return _playwright.run_check(CHECK, args, npx_available=_npx_available, build_env=_build_env)
