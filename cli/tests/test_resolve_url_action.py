"""The shell inside `.github/actions/ss-resolve-url`, run for real.

Twelve workflows depend on this one event → URL table, and its failure
modes are silent in Actions: a URL that isn't validated, a schedule that
goes red instead of skipping, a broken CLI read as "unset". So the `run:`
block is extracted from action.yml and executed under the same shell
Actions uses (`bash -e -o pipefail`), with a stub `slopstopper` on PATH.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION = REPO_ROOT / ".github" / "actions" / "ss-resolve-url" / "action.yml"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _run_block() -> str:
    """The composite step's `run: |` body, dedented."""
    lines = ACTION.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "run: |")
    indent = len(lines[start]) - len(lines[start].lstrip()) + 2
    body = []
    for line in lines[start + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body))


STUB = """#!/bin/sh
# `slopstopper config get <key>` → $STUB_<KEY>; STUB_FAIL makes it crash.
[ -n "$STUB_FAIL" ] && { echo "boom: config unreadable" >&2; exit 3; }
case "$3" in
  urls.preview)    printf '%s\\n' "$STUB_PREVIEW" ;;
  urls.production) printf '%s\\n' "$STUB_PRODUCTION" ;;
esac
"""


def resolve(tmp_path, event, mode="local", url="", deployment="", fallback="local",
            preview="", production="", cli_fails=False):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "slopstopper"
    stub.write_text(STUB)
    stub.chmod(0o755)
    out = tmp_path / "out"
    out.write_text("")
    script = tmp_path / "resolve.sh"
    script.write_text(_run_block())
    env = {
        **os.environ,
        "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
        "GITHUB_OUTPUT": str(out),
        "EVENT_NAME": event, "MODE": mode, "INPUT_URL": url,
        "DEPLOYMENT_URL": deployment, "DISPATCH_FALLBACK": fallback, "CHECK": "Test check",
        "STUB_PREVIEW": preview, "STUB_PRODUCTION": production,
        "STUB_FAIL": "1" if cli_fails else "",
    }
    proc = subprocess.run(["bash", "-e", "-o", "pipefail", str(script)], env=env,
                          capture_output=True, text=True)
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)
    return proc.returncode, outputs, proc.stdout + proc.stderr


PROD = "https://example.com"
PREVIEW = "https://preview.example.com"
LOCAL = "http://localhost:8080"


# ── mode skip: the API checks ────────────────────────────────────

@pytest.mark.parametrize(
    "event,kwargs,expected",
    [
        ("pull_request", {"preview": PREVIEW}, {"url": PREVIEW, "skip": "false", "prod": "false"}),
        ("pull_request", {}, {"url": "", "skip": "true"}),
        ("push", {"production": PROD}, {"url": PROD, "skip": "false", "prod": "true"}),
        ("push", {}, {"skip": "true"}),
        # A scheduled run with nothing configured skips — it never goes red.
        ("schedule", {}, {"skip": "true"}),
        ("schedule", {"production": PROD}, {"url": PROD, "prod": "true"}),
        # A blank manual run skips; it does not quietly probe production.
        ("workflow_dispatch", {"production": PROD}, {"skip": "true"}),
        ("workflow_dispatch", {"url": PREVIEW}, {"url": PREVIEW, "prod": "false"}),
        ("deployment_status", {"deployment": PREVIEW}, {"url": PREVIEW, "prod": "true"}),
        ("deployment_status", {}, {"skip": "true"}),
    ],
)
def test_skip_mode(tmp_path, event, kwargs, expected):
    rc, outputs, log = resolve(tmp_path, event, mode="skip", **kwargs)
    assert rc == 0, log
    for key, value in expected.items():
        assert outputs[key] == value, (key, outputs, log)
    if expected.get("skip") == "true":
        assert "::notice::" in log and "Test check" in log


# ── mode local: the browser checks ───────────────────────────────

@pytest.mark.parametrize(
    "event,kwargs,expected",
    [
        ("pull_request", {}, {"url": LOCAL, "use_local": "true"}),
        ("push", {"production": PROD}, {"url": LOCAL, "use_local": "true"}),
        ("workflow_dispatch", {}, {"url": LOCAL, "use_local": "true"}),
        ("workflow_dispatch", {"url": PREVIEW}, {"url": PREVIEW, "use_local": "false", "prod": "false"}),
        ("deployment_status", {"deployment": PREVIEW}, {"url": PREVIEW, "prod": "true"}),
        ("schedule", {"production": PROD}, {"url": PROD, "prod": "true", "use_local": "false"}),
        # CWV: a blank dispatch audits production with the dev config.
        ("workflow_dispatch", {"fallback": "production", "production": PROD},
         {"url": PROD, "prod": "false", "use_local": "false"}),
    ],
)
def test_local_mode(tmp_path, event, kwargs, expected):
    rc, outputs, log = resolve(tmp_path, event, mode="local", **kwargs)
    assert rc == 0, log
    for key, value in expected.items():
        assert outputs[key] == value, (key, outputs, log)


@pytest.mark.parametrize(
    "event,kwargs,message",
    [
        ("schedule", {}, "Scheduled run requires urls.production"),
        ("workflow_dispatch", {"fallback": "production"}, "No url input given"),
        ("deployment_status", {}, "Invalid URL format"),
    ],
)
def test_local_mode_errors(tmp_path, event, kwargs, message):
    rc, outputs, log = resolve(tmp_path, event, mode="local", **kwargs)
    assert rc != 0 and message in log
    assert "url" not in outputs


# ── failures that must end the step ──────────────────────────────

@pytest.mark.parametrize(
    "mode,event,kwargs",
    [
        ("local", "workflow_dispatch", {"url": "ftp://x"}),
        ("local", "workflow_dispatch", {"url": "javascript:alert(1)"}),
        ("local", "schedule", {"production": "ftp://x"}),
        ("local", "deployment_status", {"deployment": "not a url"}),
        ("skip", "pull_request", {"preview": "file:///etc/passwd"}),
        ("skip", "workflow_dispatch", {"url": "ftp://x"}),
    ],
)
def test_an_invalid_url_fails_the_step(tmp_path, mode, event, kwargs):
    rc, outputs, log = resolve(tmp_path, event, mode=mode, **kwargs)
    assert rc != 0, (outputs, log)
    assert "Invalid URL format" in log
    assert "url" not in outputs, "no URL may be emitted for the check to run against"


@pytest.mark.parametrize("mode,event", [("skip", "pull_request"), ("skip", "schedule"), ("local", "schedule")])
def test_a_broken_cli_is_not_an_unset_key(tmp_path, mode, event):
    rc, outputs, log = resolve(tmp_path, event, mode=mode, cli_fails=True)
    assert rc != 0
    assert "config get" in log and "failed" in log
    assert outputs == {}
