"""Guard: every third-party action is pinned to a commit, with its version alongside.

    uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6

A tag can be moved; a commit cannot. The review found zero hand-written
workflows pinned, including `pypa/gh-action-pypi-publish@release/v1`, a
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

# `uses:` as a block key or inside a flow mapping (`- {uses: x@v1}`), with any
# trailing whitespace or a CR line ending. A line the pattern misses is a
# line the guard never checks.
USES_RE = re.compile(r"^[ \t]*-?[ \t]*\{?[ \t]*uses:[ \t]*([^\s#,}]+)[^\S\n]*(#[^\r\n]*)?", re.M)
PINNED_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
# A version a reader and Dependabot can both use: `# v6`, `# v1.14.2`, `# 0.50.7`.
VERSION_COMMENT_RE = re.compile(r"^#\s*v?\d")


def _files() -> list[Path]:
    """Every workflow and composite action GitHub would run, in both extensions.
    The gh-aw lock file is generated and carries its compiler's pins."""
    workflows = [
        p for ext in ("yml", "yaml") for p in sorted(WORKFLOWS_DIR.glob(f"*.{ext}"))
        if not p.name.endswith((".lock.yml", ".lock.yaml"))
    ]
    actions = [p for name in ("action.yml", "action.yaml") for p in sorted(ACTIONS_DIR.glob(f"*/{name}"))]
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
        if not PINNED_RE.match(ref):
            floating.append(ref)
    assert not floating, f"{path.name} uses floating refs: {floating}. Pin to a commit SHA"


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


@pytest.mark.parametrize(
    "line,ref,comment",
    [
        ("      - uses: actions/checkout@v6   \n", "actions/checkout@v6", None),
        ("      - uses: actions/checkout@v6\r\n", "actions/checkout@v6", None),
        ("      - {uses: actions/checkout@v6, with: {}}\n", "actions/checkout@v6", None),
        ("        uses: a/b@" + "0" * 40 + " # v1.2.3  \n", "a/b@" + "0" * 40, "# v1.2.3  "),
    ],
)
def test_the_pattern_sees_every_uses_line(line, ref, comment):
    m = USES_RE.search(line)
    assert m and m.group(1) == ref
    assert m.group(2) == comment


@pytest.mark.parametrize("comment,ok", [("# v6", True), ("# v1.14.2", True), ("# 0.50.7", True),
                                         ("# pinned", False), ("# TODO", False), ("# release/v1", False)])
def test_a_version_comment_names_a_version(comment, ok):
    assert bool(VERSION_COMMENT_RE.match(comment)) is ok


def test_dependabot_watches_the_actions():
    config = (REPO_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: github-actions" in config
    assert '"/.github/actions/*"' in config, "the composite actions carry pins too"
    assert ".lock.yml" in config, "the gh-aw lock is generated: Dependabot must not rewrite its pins"
