"""The DAST workflow's triggers and its "Decide scan mode" shell, run for real.

PRs and pushes scan a local build; a deployment, the schedule and a
dispatch given a `url` scan the deployed site, because headers set at the
edge only exist there (#426). The URL for those comes from ss-resolve-url
(tested in test_resolve_url_action.py); this covers what the workflow
does with it.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.helpers import needs, yaml_block

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ss-security-dast-check.yml"

pytestmark = needs("bash")

STUB = """#!/bin/sh
case "$3" in
  api.openapi.spec) printf '%s\\n' "$STUB_SPEC" ;;
  urls.preview)     printf '%s\\n' "$STUB_PREVIEW" ;;
  urls.production)  printf '%s\\n' "$STUB_PRODUCTION" ;;
esac
"""


def _decide_block() -> str:
    return yaml_block(WORKFLOW, "run", step="Decide scan mode").replace("${{ github.event_name }}", "$EVENT")


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


def test_a_configured_api_url_with_ipv6_query_and_fragment_is_accepted(tmp_path):
                  url = "https://[2001:db8::1]:8443/openapi?version=1#api"
                  assert decide(tmp_path, "workflow_dispatch", spec="openapi.yaml", production=url) == {
                      "mode": "api", "url": url,
                  }


def test_dast_passes_resolved_url_through_a_quoted_environment_variable():
                  text = WORKFLOW.read_text()
                  run_block = yaml_block(WORKFLOW, "run", step="Run DAST analysis + gate")
                  assert "TARGET_URL: ${{ steps.mode.outputs.url }}" in text
                  assert 'task -x ss:security:dast -- "$TARGET_URL"' in run_block


def test_the_workflow_takes_a_url_and_runs_on_schedule_and_successful_deployments():
    text = WORKFLOW.read_text()
    assert re.search(r"workflow_dispatch:\n\s+inputs:\n\s+url:", text)
    assert re.search(r"schedule:\n\s+- cron:", text)
    assert "deployment_status:" in text
    assert "github.event.deployment_status.state == 'success'" in text


def test_a_scanner_error_fails_the_scan_step_itself():
    """No continue-on-error: the step that ran ZAP is the one that goes red,
    and only blocking alerts (rc 1) open the issue on main (#455)."""
    text = WORKFLOW.read_text()
    assert "continue-on-error" not in text
    assert "Fail job if gate" not in text
    run_block = yaml_block(WORKFLOW, "run", step="Run DAST analysis + gate")
    assert "task -x ss:security:dast" in run_block
    assert 'echo "rc=$rc" >> "$GITHUB_OUTPUT"' in run_block
    assert "steps.dast.outputs.rc == '1'" in text
    for step in ("Emit PR comment", "Emit issue on main", "Close issue on main"):
        assert re.search(rf"- name: {step}.*?\n\s+(?:#.*\n\s+)*if: always\(\)", text, re.S), step
