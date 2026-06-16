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
from pathlib import Path

from slopstopper import config, output, templates

SPEC_NAME = "smoke"
REPORT_DIR = Path(".ss/reports/reliability")
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


def _ensure_playwright_assets_ejected() -> None:
    """Auto-eject the playwright config and the spec we're about to run.

    The bundled assets live inside the pipx venv where node_modules
    can't be resolved by Playwright. Ejecting into `.ss/` (in the
    adopter's CWD) puts them next to node_modules. Idempotent: silent
    on re-runs.
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
    """Write a minimal markdown summary consumable by `slopstopper emit`.

    Playwright's own HTML report at `playwright-report/` is the source of
    truth for failure detail; this report just summarises pass/fail and
    points at it.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    status = "✅ PASSED" if exit_code == 0 else "❌ FAILED"
    lines = [
        "## Smoke Test Results",
        "",
        f"**Status:** {status}",
        f"**Target:** `{url}`",
    ]
    if exit_code != 0:
        lines += [
            "",
            "The smoke tests are failing. Investigate the failing assertion in the "
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
        output.error("smoke target URL is required")
        output._emit("Usage:")
        output._emit("  slopstopper run reliability:smoke -- --url https://your-site.example.com")
        output._emit("  SMOKE_TEST_URL=https://your-site slopstopper run reliability:smoke")
        return 1

    output.running(f"Running smoke tests against: {url}")
    _ensure_playwright_assets_ejected()
    env = _build_env(url, parsed.ci)
    cmd = _build_cmd(parsed.ci)
    result = subprocess.run(cmd, env=env, check=False)
    _write_report(result.returncode, url)
    return result.returncode
