"""The shell inside `ss-cloudflare-deployed.yml`, run for real.

It runs on main after every Workers Builds deploy, so a PR-only problem
(no preview URL yet, a fork) must not fail it, and one refused dispatch
must not drop the rest. `gh`, `slopstopper` and `sleep` are stubs on PATH.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.helpers import needs, yaml_block

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ss-cloudflare-deployed.yml"

pytestmark = needs("bash")

GH = """#!/bin/sh
# gh stub: `pr list` → $STUB_PR_LINE; `api` → $STUB_COMMENTS; `workflow run` fails for $STUB_REFUSE.
case "$1 $2" in
  "pr list") printf '%s\\n' "$STUB_PR_LINE" ;;
  "api "*)   printf '%s\\n' "$STUB_COMMENTS" ;;
  "workflow run")
    echo "run $3" >> "$STUB_LOG"
    if [ "$3" = "$STUB_REFUSE" ]; then echo "HTTP 422: Unexpected inputs provided" >&2; exit 1; fi
    ;;
esac
"""
SS = """#!/bin/sh
case "$1 $2" in
  "config get")   printf '%s\\n' "$STUB_PRODUCTION" ;;
  "cloudflare preview-url") [ -n "$STUB_PREVIEW" ] && printf '%s\\n' "$STUB_PREVIEW" || exit 1 ;;
  "profile disabled") printf '%s\\n' "$STUB_DISABLED" ;;
esac
"""


def _bin(tmp_path: Path) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    for name, body in [("gh", GH), ("slopstopper", SS), ("sleep", "#!/bin/sh\nexit 0\n")]:
        (bindir / name).write_text(body)
        (bindir / name).chmod(0o755)
    return bindir


def _sh(tmp_path: Path, step: str, env: dict[str, str]) -> tuple[int, dict[str, str], str]:
    out = tmp_path / "out"
    out.write_text("")
    log = tmp_path / "dispatched"
    log.write_text("")
    script = tmp_path / "step.sh"
    script.write_text(yaml_block(WORKFLOW, "run", step=step))
    (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    full = {**os.environ, "PATH": f"{_bin(tmp_path)}{os.pathsep}{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(out), "GITHUB_REPOSITORY": "o/r", "STUB_LOG": str(log),
            "STUB_PR_LINE": "", "STUB_COMMENTS": "", "STUB_PREVIEW": "", "STUB_PRODUCTION": "",
            "STUB_DISABLED": "", "STUB_REFUSE": "", **env}
    proc = subprocess.run(["bash", "-e", "-o", "pipefail", str(script)], cwd=tmp_path, env=full,
                          capture_output=True, text=True)
    outputs = dict(l.split("=", 1) for l in out.read_text().splitlines() if "=" in l)
    return proc.returncode, outputs, proc.stdout + proc.stderr


TARGET = {"BRANCH": "feat-x", "SHA": "1a2b3c4d5e6f", "DEFAULT_BRANCH": "main"}


def test_a_preview_url_is_resolved_from_the_pr_comment(tmp_path):
    rc, out, log = _sh(tmp_path, "Work out what was deployed and where",
                       {**TARGET, "STUB_PR_LINE": "7 o", "STUB_PREVIEW": "https://1a2b3c4d-r.o.workers.dev/"})
    assert rc == 0, log
    assert out == {"url": "https://1a2b3c4d-r.o.workers.dev/", "branch": "feat-x", "production": "false"}


def test_no_preview_url_yet_is_a_warning_not_a_failure_on_main(tmp_path):
    rc, out, log = _sh(tmp_path, "Work out what was deployed and where", {**TARGET, "STUB_PR_LINE": "7 o"})
    assert rc == 0, log
    assert "url" not in out and "::warning::" in log and "::error::" not in log


def test_a_fork_pr_is_skipped_with_a_notice(tmp_path):
    rc, out, log = _sh(tmp_path, "Work out what was deployed and where",
                       {**TARGET, "STUB_PR_LINE": "7 someone-else", "STUB_PREVIEW": "https://x.o.workers.dev/"})
    assert rc == 0, log
    assert "url" not in out and "fork" in log


def test_main_resolves_to_production(tmp_path):
    rc, out, log = _sh(tmp_path, "Work out what was deployed and where",
                       {**TARGET, "BRANCH": "main", "STUB_PRODUCTION": "https://example.com"})
    assert rc == 0, log
    assert out["url"] == "https://example.com" and out["production"] == "true"


def _dispatch(tmp_path, production: str, refuse: str = "", disabled: str = ""):
    for wf in ["ss-reliability-smoke-tests.yml", "ss-reliability-seo-check.yml",
               "ss-reliability-api-health-check.yml", "ss-security-dast-check.yml"]:
        (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".github" / "workflows" / wf).write_text("")
    rc, _, log = _sh(tmp_path, "Dispatch the URL-driven checks",
                     {"URL": "https://example.com", "BRANCH": "main", "PRODUCTION": production,
                      "STUB_REFUSE": refuse, "STUB_DISABLED": disabled})
    return rc, (tmp_path / "dispatched").read_text().split(), log


def test_a_refused_dispatch_does_not_drop_the_rest(tmp_path):
    rc, ran, log = _dispatch(tmp_path, "true", refuse="ss-reliability-seo-check.yml")
    assert rc == 1
    assert ran == ["run", "ss-reliability-smoke-tests.yml", "run", "ss-reliability-seo-check.yml",
                   "run", "ss-reliability-api-health-check.yml", "run", "ss-security-dast-check.yml"]
    assert "::warning::ss-reliability-seo-check.yml was not dispatched" in log


def test_disabled_and_missing_workflows_are_not_dispatched_and_dast_is_production_only(tmp_path):
    rc, ran, log = _dispatch(tmp_path, "false", disabled="ss-reliability-api-health-check.yml")
    assert rc == 0, log
    assert ran == ["run", "ss-reliability-smoke-tests.yml", "run", "ss-reliability-seo-check.yml"]
