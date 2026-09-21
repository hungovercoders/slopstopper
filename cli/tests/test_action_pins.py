"""Guard: every third-party action is pinned to a commit, with its version alongside.

    uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6

A tag can be moved; a commit cannot. The review found zero hand-written
workflows pinned — including `pypa/gh-action-pypi-publish@release/v1`, a
mutable *branch*, on the job that publishes to PyPI with `id-token:
write`. A security-tooling product that ships SAST and secrets scanning
into other people's repos should not itself run whatever a moved tag
points at. Dependabot (`.github/dependabot.yml`) keeps the pins current.

The version comment is required too: it is what a human reads in a diff,
and what Dependabot updates alongside the SHA.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github/workflows"
ACTIONS_DIR = REPO_ROOT / ".github/actions"

USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)(\s*#.*)?$", re.M)
PINNED_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"^\s*#\s*\S+")

# Deferred, not exempt: #339 deletes these two from every ss-* workflow and
# re-homes them in .github/actions/ss-setup, where they are pinned. Pinning
# them here as well would conflict with that PR on 23 files. Remove this set
# once #339 has merged; the assertion below then covers them.
DEFERRED_IN_SS_WORKFLOWS = {"actions/setup-python", "jdx/mise-action"}


def _files() -> list[Path]:
    workflows = [p for p in sorted(WORKFLOWS_DIR.glob("*.yml")) if not p.name.endswith(".lock.yml")]
    actions = sorted(ACTIONS_DIR.glob("*/action.yml")) if ACTIONS_DIR.is_dir() else []
    return workflows + actions


def _uses(path: Path) -> list[tuple[str, str]]:
    """(ref, trailing_comment) for every third-party `uses:` in the file."""
    out = []
    for m in USES_RE.finditer(path.read_text(encoding="utf-8")):
        ref = m.group(1)
        if ref.startswith("./") or ref.startswith("docker://"):
            continue
        out.append((ref, m.group(2) or ""))
    return out


def test_the_fixture_finds_workflows():
    assert len(_files()) >= 20
    assert sum(len(_uses(p)) for p in _files()) >= 50


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_every_third_party_action_is_pinned_to_a_commit(path):
    floating = []
    for ref, _comment in _uses(path):
        repo = ref.rsplit("@", 1)[0]
        if path.name.startswith("ss-") and path.name != "ss-release.yml" and repo in DEFERRED_IN_SS_WORKFLOWS:
            continue
        if not PINNED_RE.match(ref):
            floating.append(ref)
    assert not floating, f"{path.name} uses floating refs: {floating} — pin to a commit SHA"


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_every_pinned_action_says_which_version_it_is(path):
    unlabelled = []
    for ref, comment in _uses(path):
        if PINNED_RE.match(ref) and not VERSION_COMMENT_RE.match(comment):
            unlabelled.append(ref)
    assert not unlabelled, (
        f"{path.name}: pinned without a version comment (`# vN`), so nobody can read "
        f"the diff and Dependabot can't track it: {unlabelled}"
    )


def test_dependabot_watches_the_actions():
    config = (REPO_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: github-actions" in config
    assert '"/.github/actions/*"' in config, "the composite actions carry pins too"
