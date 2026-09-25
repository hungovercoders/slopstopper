"""What the three Playwright-backed checks share.

smoke, accessibility and broken-links each drive a bundled Playwright
spec against a URL and write a short pass/fail summary pointing at
Playwright's own HTML report. The spec name and the wording differ; the
plumbing was copied three times.

The eject dance is the non-obvious part and is documented once, here:
the bundled config and specs live inside the pipx venv, where Playwright
cannot resolve `node_modules`. Ejecting them into `.ss/` in the
adopter's CWD puts them next to `node_modules`. It is idempotent.
"""

from __future__ import annotations

from pathlib import Path

from slopstopper import output, templates
from slopstopper.checks import _report


def ensure_assets_ejected(spec_name: str) -> None:
    """Eject the Playwright config and `tests/<spec_name>.spec.ts` if not already."""
    for name in (templates.PLAYWRIGHT_CONFIG_NAME, f"tests/{spec_name}.spec.ts"):
        dest, was_new = templates.ensure_ejected(name)
        if was_new:
            output.info(f"ejected {dest} (Playwright must run from a path with node_modules reachable)")


def build_cmd(spec_name: str, ci_mode: bool) -> list[str]:
    # `json` feeds `_contract.playwright_ran`: Playwright exits 1 both when
    # tests failed and when they never ran, and only the report can tell.
    reporter = "list,html,json" if ci_mode else "list,json"
    return [
        "npx", "playwright", "test",
        f"--config={templates.playwright_config()}",
        str(templates.playwright_spec(spec_name)),
        f"--reporter={reporter}",
    ]


def write_summary(
    report_dir: Path,
    md_path: Path,
    title: str,
    exit_code: int,
    url: str,
    failure_hint: str,
) -> None:
    """A minimal markdown summary consumable by `slopstopper emit`.

    Playwright's HTML report at `playwright-report/` is the source of
    truth for failure detail; this just summarises pass/fail, points at
    it, and links the workflow run when there is one.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    status = "✅ PASSED" if exit_code == 0 else "❌ FAILED"
    lines = [title, "", f"**Status:** {status}", f"**Target:** `{url}`"]
    if exit_code != 0:
        lines += ["", failure_hint]
        run_url = _report.gha_run_url()  # looked up at call time, so patching _report works
        if run_url:
            lines += ["", f"[View the workflow run]({run_url})"]
    md_path.write_text("\n".join(lines) + "\n")
