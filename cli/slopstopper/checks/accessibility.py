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
both bind in via the adopter's node_modules. Page discovery uses the
in-CLI slopstopper.discovery module.

Falls back to SMOKE_TEST_URL when ACCESSIBILITY_TEST_URL is unset,
matching the bash flow exactly.

Configuration (.slopstopper.yml — all optional):

    pages:
      accessibility: /,/blog,/about
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
from pathlib import Path

from slopstopper import discovery, output, templates

SPEC_NAME = "accessibility"
REPORT_DIR = Path(".ss/reports/reliability")
REPORT_MD = REPORT_DIR / "accessibility-report.md"

# Consumed by `slopstopper emit reliability:accessibility --target {pr-comment,issue}`.
# Issue title + label match the strings the legacy workflow used in raw
# `gh issue create` so existing open issues continue to dedup post-migration.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "## ♿ Accessibility Audit Results",
    "issue_title": "♿ Accessibility Violations Detected on Main Branch",
    "issue_labels": ["accessibility", "reliability"],
    "issue_followup": "🔔 Accessibility violations recurred in commit",
    "issue_close_comment": "✅ Accessibility audit is now passing on `main`. Closing automatically.",
}


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="slopstopper run reliability:accessibility", add_help=False
    )
    p.add_argument(
        "url_positional",
        nargs="?",
        default=None,
        help="Site URL to audit (alternative to --url; e.g. http://localhost:8080)",
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


def _ensure_playwright_assets_ejected() -> None:
    """Auto-eject the playwright config and the spec we're about to run.

    The bundled assets live inside the pipx venv where node_modules
    can't be resolved by Playwright. Ejecting into `.ss/` puts them in
    the adopter's CWD where node_modules IS reachable. Idempotent.
    """
    for name in (templates.PLAYWRIGHT_CONFIG_NAME, f"tests/{SPEC_NAME}.spec.ts"):
        dest, was_new = templates.ensure_ejected(name)
        if was_new:
            output.info(f"ejected {dest} (Playwright must run from a path with node_modules reachable)")


def _build_cmd(ci_mode: bool) -> list[str]:
    reporter = "list,html" if ci_mode else "list"
    return [
        "npx", "playwright", "test",
        f"--config={templates.playwright_config()}",
        str(templates.playwright_spec(SPEC_NAME)),
        f"--reporter={reporter}",
    ]


def _gha_run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not (server and repo and run_id):
        return None
    return f"{server}/{repo}/actions/runs/{run_id}"


def _write_report(exit_code: int, url: str) -> None:
    """Write a minimal markdown summary consumable by `slopstopper emit`."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    status = "✅ PASSED" if exit_code == 0 else "❌ FAILED"
    lines = [
        "## ♿ Accessibility Audit Results",
        "",
        f"**Status:** {status}",
        f"**Target:** `{url}`",
    ]
    if exit_code != 0:
        lines += [
            "",
            "Accessibility violations detected. Investigate the failing assertions in the "
            "[Playwright HTML report](playwright-report/index.html) "
            "(uploaded as an artifact in CI).",
        ]
        run_url = _gha_run_url()
        if run_url:
            lines += ["", f"[View the workflow run]({run_url})"]
    REPORT_MD.write_text("\n".join(lines) + "\n")


def run(args: list[str] | None = None) -> int:
    if not _npx_available():
        output.error("npx is not available — install Node.js to run Playwright tests")
        return 1

    parsed = _parse_args(args)
    url = _resolve_url(parsed.url_positional or parsed.url)
    if not url:
        output.error("accessibility target URL is required")
        output._emit("Usage:")
        output._emit("  slopstopper run reliability:accessibility -- --url https://your-site.example.com")
        output._emit("  ACCESSIBILITY_TEST_URL=https://your-site slopstopper run reliability:accessibility")
        return 1

    _ensure_playwright_assets_ejected()
    spec = templates.playwright_spec(SPEC_NAME)
    if not spec.exists():
        output.error(f"Accessibility spec not found at {spec}")
        output._emit("   The spec is bundled inside slopstopper-cli; reinstall to repair.")
        return 1

    output.status("♿", f"Running accessibility audit against: {url}")
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    result = subprocess.run(cmd, env=env, check=False)
    _write_report(result.returncode, url)
    return result.returncode
