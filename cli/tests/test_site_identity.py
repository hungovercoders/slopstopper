"""The one-sentence identity is copied into every surface that describes the
project. Nothing else compares prose, so this test does: it fails when any
copy drifts from the others. Change them all together, or change IDENTITY
here with them. docs/app/README.md lists the surfaces.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

IDENTITY = (
    "A Python CLI plus GitHub Actions workflows that run security, hygiene "
    "and reliability checks on every PR. One command to install into any repo."
)

# file -> how many verbatim copies it must hold.
SURFACES = {
    "app/index.html": 3,            # og:description, twitter:description, hero
    "app/manifest.webmanifest": 1,
    "README.md": 1,
    "cli/README.md": 1,
    "cli/pyproject.toml": 1,
    ".claude/skills/slopstopper-install/SKILL.md": 1,
}


def _text(rel: str) -> str:
    path = REPO_ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} not present (running outside the repo checkout)")
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(("rel", "copies"), sorted(SURFACES.items()))
def test_identity_sentence_is_verbatim(rel: str, copies: int) -> None:
    assert _text(rel).count(IDENTITY) == copies, (
        f"{rel}: expected {copies} verbatim copies of the identity sentence; "
        "see docs/app/README.md (content authoring rules)"
    )


def test_meta_description_starts_with_identity() -> None:
    html = _text("app/index.html")
    match = re.search(r'<meta name="description" content="([^"]*)"', html)
    assert match, "home page has no meta description"
    lowered = IDENTITY[0].lower() + IDENTITY[1:]
    assert match.group(1) == f"SlopStopper \u2014 {lowered}"
    assert len(match.group(1)) <= 160


def test_llms_txt_blockquote_opens_with_identity() -> None:
    text = _text("app/llms.txt")
    quote = " ".join(
        line[1:].strip() for line in text.splitlines() if line.startswith(">")
    )
    assert quote.startswith(IDENTITY)
