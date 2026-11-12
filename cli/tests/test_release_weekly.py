"""The shell inside `release-weekly.yml`, run for real.

It merges the Release PR, which tags a release and publishes to PyPI, so
the cases that must not merge matter more than the one that does: no
Release PR, a failing check, checks it could not read. `gh` and `sleep`
are stubs on PATH.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from tests.helpers import needs, yaml_block

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-weekly.yml"
STEP = "Merge the Release PR if its checks are green"

pytestmark = needs("bash", "jq")

GH = """#!/bin/sh
# gh stub: `pr list` → $STUB_PR; `pr checks` → pending for $STUB_PENDING_ROUNDS
# calls, then $STUB_CHECKS with exit $STUB_CHECKS_RC; `pr merge` is logged.
echo "$*" >> "$STUB_LOG"
case "$1 $2" in
  "pr list") printf '%s' "$STUB_PR" ;;
  "pr checks")
    n=$(cat "$STUB_COUNT" 2>/dev/null || echo 0)
    echo $((n + 1)) > "$STUB_COUNT"
    if [ "$n" -lt "$STUB_PENDING_ROUNDS" ]; then
      echo '[{"name":"smoke","bucket":"pending"}]'; exit 8
    fi
    printf '%s' "$STUB_CHECKS"; exit "$STUB_CHECKS_RC"
    ;;
esac
"""
PR = '{"number":7,"title":"chore(main): release 1.2.3","headRefOid":"abcdef1234567"}'
GREEN = '[{"name":"smoke","bucket":"pass"},{"name":"dast","bucket":"skipping"}]'


def _run(tmp_path: Path, **env: str) -> tuple[int, list[str], str]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in [("gh", GH), ("sleep", "#!/bin/sh\nexit 0\n")]:
        (bindir / name).write_text(body)
        (bindir / name).chmod(0o755)
    script = tmp_path / "step.sh"
    script.write_text(yaml_block(WORKFLOW, "run", step=STEP))
    log = tmp_path / "gh.log"
    log.write_text("")
    full = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
            "STUB_LOG": str(log), "STUB_COUNT": str(tmp_path / "count"), "STUB_PR": "",
            "STUB_CHECKS": "", "STUB_CHECKS_RC": "0", "STUB_PENDING_ROUNDS": "0", **env}
    proc = subprocess.run(["bash", "-e", "-o", "pipefail", str(script)], cwd=tmp_path, env=full,
                          capture_output=True, text=True)
    merges = [line for line in log.read_text().splitlines() if line.startswith("pr merge")]
    return proc.returncode, merges, proc.stdout + proc.stderr


def test_no_release_pr_is_a_pass_and_merges_nothing(tmp_path):
    rc, merges, out = _run(tmp_path)
    assert rc == 0, out
    assert merges == []
    assert "nothing to release this week" in out


def test_a_green_release_pr_is_squash_merged_at_the_commit_that_was_checked(tmp_path):
    rc, merges, out = _run(tmp_path, STUB_PR=PR, STUB_CHECKS=GREEN)
    assert rc == 0, out
    assert merges == ["pr merge 7 --squash --match-head-commit abcdef1234567"]


def test_a_draft_release_pr_is_held_back(tmp_path):
    draft = PR.replace("}", ',"isDraft":true}')
    rc, merges, out = _run(tmp_path, STUB_PR=draft, STUB_CHECKS=GREEN)
    assert rc == 0, out
    assert merges == []
    assert "is a draft" in out


def test_a_failing_check_fails_the_run_and_merges_nothing(tmp_path):
    checks = '[{"name":"smoke","bucket":"fail"},{"name":"e2e","bucket":"pass"}]'
    rc, merges, out = _run(tmp_path, STUB_PR=PR, STUB_CHECKS=checks, STUB_CHECKS_RC="1")
    assert rc == 1
    assert merges == []
    assert "is not green (smoke)" in out


def test_a_cancelled_check_is_not_green(tmp_path):
    rc, merges, _ = _run(tmp_path, STUB_PR=PR, STUB_CHECKS='[{"name":"smoke","bucket":"cancel"}]')
    assert rc == 1 and merges == []


def test_pending_checks_are_waited_for(tmp_path):
    rc, merges, out = _run(tmp_path, STUB_PR=PR, STUB_CHECKS=GREEN, STUB_PENDING_ROUNDS="2")
    assert rc == 0, out
    assert len(merges) == 1
    assert out.count("still running") == 2


def test_checks_that_cannot_be_read_merge_nothing(tmp_path):
    rc, merges, out = _run(tmp_path, STUB_PR=PR, STUB_CHECKS="", STUB_CHECKS_RC="1")
    assert rc == 1
    assert merges == []
    assert "Could not read the checks" in out


def test_the_merge_is_made_with_the_release_bots_token():
    """A merge by GITHUB_TOKEN pushes a commit that starts no workflow, so
    release-please would never tag the release."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "GH_TOKEN: ${{ steps.app-token.outputs.token }}" in text
    assert "secrets.GITHUB_TOKEN" not in text and "github.token" not in text
    please = (WORKFLOW.parent / "release-please.yml").read_text(encoding="utf-8")
    pin = re.search(r"actions/create-github-app-token@\S+", please).group(0)
    assert pin in text, "mint the token with the same pinned action release-please.yml uses"
