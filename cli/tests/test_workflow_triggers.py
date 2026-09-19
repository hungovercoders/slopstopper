"""Guard: every check workflow appears in ss-pr-summary.yml's trigger list.

`ss-pr-summary.yml` re-renders the single rolling PR comment on
`workflow_run`, and GitHub does not support globs there — each workflow
must be named in full. A workflow left out of the list still runs and
still posts its own comment, but the summary silently stops re-rendering
after it, so the headline count goes stale without anything going red.

The requirement is documented in AGENTS.md and both skills; nothing
enforced it until this test, and adding checks is exactly when it bites.

Parsed with a small line reader rather than a YAML library: the CLI
ships no third-party dependencies and the test suite holds the same
line.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github/workflows"
SUMMARY_WORKFLOW = WORKFLOWS_DIR / "ss-pr-summary.yml"

# Workflows that are not checks and so have no place in the summary:
#   ss-pr-summary          the summary itself — it would trigger on itself
#   ss-release             publishes the CLI; not a PR verdict
#   ss-workflow-failure-issue  reacts to failures on main, not PRs
#   ss-hygiene-doc-updater.lock  the agentic doc updater; opens a PR, isn't a check
NON_CHECK_WORKFLOWS = {
    "ss-pr-summary.yml",
    "ss-release.yml",
    "ss-workflow-failure-issue.yml",
    "ss-hygiene-doc-updater.lock.yml",
}


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _workflow_name(path: Path) -> str | None:
    """The workflow's top-level `name:`, unquoted."""
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^name:\s*(.+)$", line)
        if match:
            return _unquote(match.group(1))
    return None


def _trigger_list() -> list[str]:
    """The `workflow_run.workflows` entries from ss-pr-summary.yml."""
    lines = SUMMARY_WORKFLOW.read_text(encoding="utf-8").splitlines()
    names: list[str] = []
    inside = False
    for line in lines:
        if re.match(r"^\s+workflows:\s*$", line):
            inside = True
            continue
        if not inside:
            continue
        match = re.match(r"^\s+-\s+(.+)$", line)
        if match:
            names.append(_unquote(match.group(1)))
        elif line.strip():
            break
    return names


def _check_workflows() -> dict[str, str]:
    """{filename: workflow name} for every ss-*.yml that is a check."""
    out = {}
    for path in sorted(WORKFLOWS_DIR.glob("ss-*.yml")):
        if path.name in NON_CHECK_WORKFLOWS:
            continue
        name = _workflow_name(path)
        assert name, f"{path.name} has no top-level `name:`"
        out[path.name] = name
    return out


def test_the_fixture_finds_workflows():
    """Sanity: a broken glob would make every assertion below vacuous."""
    assert len(_check_workflows()) >= 15
    assert len(_trigger_list()) >= 15


def test_every_check_workflow_is_in_the_summary_trigger_list():
    triggers = set(_trigger_list())
    missing = {
        filename: name for filename, name in _check_workflows().items() if name not in triggers
    }
    assert not missing, (
        "These check workflows are missing from ss-pr-summary.yml's "
        "`workflow_run.workflows` list, so the PR summary will never re-render "
        f"after them: {missing}"
    )


def test_the_trigger_list_names_no_workflow_that_does_not_exist():
    """A renamed workflow leaves a dead entry behind, which is just as silent."""
    known = set(_check_workflows().values())
    unknown = [name for name in _trigger_list() if name not in known]
    assert not unknown, (
        "ss-pr-summary.yml triggers on workflows that no longer exist under "
        f"these names: {unknown}"
    )


def test_the_trigger_list_has_no_duplicates():
    triggers = _trigger_list()
    assert len(triggers) == len(set(triggers))


@pytest.mark.parametrize(
    "filename",
    ["ss-reliability-api-latency-check.yml", "ss-hygiene-openapi-check.yml"],
)
def test_the_newest_checks_are_covered(filename):
    """Named explicitly so a deletion can't quietly shrink the guard."""
    assert _workflow_name(WORKFLOWS_DIR / filename) in set(_trigger_list())
