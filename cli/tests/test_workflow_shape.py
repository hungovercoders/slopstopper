"""Guard: the ss-* workflows share their plumbing through the composite actions.

Before `.github/actions/ss-setup` and `ss-resolve-url` existed, the same
three toolchain steps were copied into 24 workflows and the same
`validate_url()` shell function into 12, with four mutually incompatible
`if:` dialects on the emit step growing around them. Copies drift — that
is how two workflows ended up never deleting their PR comment.

These tests keep the plumbing in one place: no ss-* workflow may inline
what the actions provide, every local `uses:` must resolve, and every
`steps.<id>.outputs` reference must name a step that exists (a renamed
step id fails silently in Actions — the expression just evaluates empty).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github/workflows"
ACTIONS_DIR = REPO_ROOT / ".github/actions"

# Not built on the composite actions: they aren't checks and don't need the
# CLI toolchain (or, for the release, need a different Python setup).
EXEMPT = {
    "ss-release.yml",
    "ss-hygiene-auto-label-pr.yml",
    "ss-hygiene-doc-updater.lock.yml",
    "ss-security-vulnerability-new-check.yml",
    "ss-workflow-failure-issue.yml",
}

WORKFLOWS = sorted(p.name for p in WORKFLOWS_DIR.glob("ss-*.yml"))
BUILT_ON_ACTIONS = [w for w in WORKFLOWS if w not in EXEMPT]


def _text(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def test_the_composite_actions_exist():
    for action in ("ss-setup", "ss-resolve-url"):
        assert (ACTIONS_DIR / action / "action.yml").is_file(), action


def test_the_fixture_finds_workflows():
    assert len(BUILT_ON_ACTIONS) >= 15


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_workflow_sets_up_through_the_composite_action(workflow):
    text = _text(workflow)
    assert "uses: ./.github/actions/ss-setup" in text, f"{workflow} does not use ss-setup"
    for inlined in ("jdx/mise-action", "actions/setup-python", "pip install -e ./cli"):
        assert inlined not in text, (
            f"{workflow} inlines `{inlined}` — that step lives in .github/actions/ss-setup"
        )


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_workflow_does_not_inline_url_resolution(workflow):
    assert "validate_url()" not in _text(workflow), (
        f"{workflow} defines validate_url() — URL resolution lives in .github/actions/ss-resolve-url"
    )


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_ss_setup_follows_checkout(workflow):
    """A later `pip install <tool>` or `npm ci` relies on the Python and
    node that ss-setup puts on PATH, so it has to come first."""
    names = re.findall(r"^      - name: (.+)$", _text(workflow), re.M)
    assert names[0].startswith("Checkout"), workflow
    assert names[1] == "Set up slopstopper", f"{workflow}: second step is {names[1]!r}"


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_every_local_action_reference_resolves(workflow):
    for ref in re.findall(r"uses: \./\.github/actions/([A-Za-z0-9_-]+)", _text(workflow)):
        assert (ACTIONS_DIR / ref / "action.yml").is_file(), f"{workflow} uses missing action {ref}"


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_every_step_output_reference_names_a_real_step(workflow):
    text = _text(workflow)
    ids = set(re.findall(r"^\s+id:\s*(\S+)\s*$", text, re.M))
    refs = set(re.findall(r"steps\.([A-Za-z0-9_-]+)\.", text))
    assert refs <= ids, f"{workflow} references steps that don't exist: {sorted(refs - ids)}"


def test_resolve_url_declares_the_outputs_the_workflows_read():
    action = (ACTIONS_DIR / "ss-resolve-url" / "action.yml").read_text(encoding="utf-8")
    declared = set(re.findall(r"^  ([a-z_]+):\n    description", action, re.M))
    used: set[str] = set()
    for workflow in BUILT_ON_ACTIONS:
        text = _text(workflow)
        if "ss-resolve-url" not in text:
            continue
        step_id = re.search(r"id: (\S+)\n(?:.*\n){0,5}?\s+uses: \./\.github/actions/ss-resolve-url", text)
        assert step_id, workflow
        used |= set(re.findall(rf"steps\.{re.escape(step_id.group(1))}\.outputs\.([a-z_]+)", text))
    assert used <= declared, f"workflows read outputs ss-resolve-url doesn't declare: {sorted(used - declared)}"
