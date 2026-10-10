"""The DAST workflow's triggers and its "Decide scan mode" shell, run for real.

PRs and pushes scan a local build; a deployment, the schedule and a
dispatch given a `url` scan the deployed site, because headers set at the
edge only exist there (#426). The URL for those comes from ss-resolve-url
(tested in test_resolve_url_action.py); this covers what the workflow
does with it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ss-security-dast-check.yml"

STUB = """#!/bin/sh
case "$3" in
  api.openapi.spec) printf '%s\\n' "$STUB_SPEC" ;;
  urls.preview)     printf '%s\\n' "$STUB_PREVIEW" ;;
  urls.production)  printf '%s\\n' "$STUB_PRODUCTION" ;;
esac
"""


def _decide_block() -> str:
    lines = WORKFLOW.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "- name: Decide scan mode")
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    indent = len(lines[run_at]) - len(lines[run_at].lstrip()) + 2
    body = []
    for line in lines[run_at + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).replace("${{ github.event_name }}", "$EVENT")


def decide(tmp_path, event, remote="skipped", remote_url="", remote_skip="", spec="", preview="", production=""):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    (bindir / "slopstopper").write_text(STUB)
    (bindir / "slopstopper").chmod(0o755)
    out = tmp_path / "out"
    out.write_text("")
    script = tmp_path / "decide.sh"
    script.write_text(_decide_block())
    env = {
        **os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "GITHUB_OUTPUT": str(out),
        "EVENT": event, "REMOTE": remote, "REMOTE_URL": remote_url, "REMOTE_SKIP": remote_skip,
        "STUB_SPEC": spec, "STUB_PREVIEW": preview, "STUB_PRODUCTION": production,
    }
    proc = subprocess.run(["bash", "-e", "-o", "pipefail", str(script)], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)


pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

LIVE = "https://example.com"


@pytest.mark.parametrize("event", ["pull_request", "push", "workflow_dispatch"])
def test_prs_pushes_and_a_blank_dispatch_scan_a_local_build(tmp_path, event):
    assert decide(tmp_path, event) == {"mode": "site", "url": "http://localhost:8080"}


@pytest.mark.parametrize("event", ["deployment_status", "schedule", "workflow_dispatch"])
def test_a_resolved_deployed_url_is_scanned_without_a_build(tmp_path, event):
    assert decide(tmp_path, event, remote="success", remote_url=LIVE, remote_skip="false") == {
        "mode": "deployed", "url": LIVE,
    }


def test_a_schedule_with_no_production_url_skips(tmp_path):
    assert decide(tmp_path, "schedule", remote="success", remote_skip="true") == {"mode": "skip"}


def test_a_deployed_api_with_a_spec_is_an_api_scan(tmp_path):
    assert decide(tmp_path, "schedule", remote="success", remote_url=LIVE, remote_skip="false",
                  spec="openapi.yaml") == {"mode": "api", "url": LIVE}


def test_the_workflow_takes_a_url_and_runs_on_schedule_and_successful_deployments():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:\n    inputs:\n      url:" in text
    assert "schedule:\n    - cron:" in text
    assert "deployment_status:" in text
    assert "github.event.deployment_status.state == 'success'" in text
