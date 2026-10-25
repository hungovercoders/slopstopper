"""The course's sample output names the current release.

Lesson 1 shows the installer pinning `slopstopper-cli` and the pin in
`mise.toml`; the version in those samples is the one on PyPI when the
lesson was written, which the next release makes stale. release-please
bumps `cli/pyproject.toml` on the release PR, so this test turns red
there and the lesson is refreshed in the same PR, rather than a reader
comparing their screen with last month's number (#548).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEARN = REPO_ROOT / "docs" / "learn"

# `slopstopper-cli@0.25.0`, `slopstopper-cli installed (0.25.0`, `"pipx:slopstopper-cli" = "0.25.0"`.
_VERSION_SAMPLE = re.compile(r'slopstopper-cli(?:@|" = "| installed \()(\d+\.\d+\.\d+)')


def _cli_version() -> str:
    data = tomllib.loads((REPO_ROOT / "cli" / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def test_lesson_samples_pin_the_current_release():
    current = _cli_version()
    stale = []
    for page in sorted(LEARN.glob("[0-9]*.md")):
        for m in _VERSION_SAMPLE.finditer(page.read_text(encoding="utf-8")):
            if m.group(1) != current:
                stale.append(f"{page.name}: {m.group(0)} (current {current})")
    assert not stale, "lesson samples name a release that is not the current one; refresh them:\n" + "\n".join(stale)


def test_the_regex_sees_the_three_sample_shapes():
    text = 'Pinning slopstopper-cli@0.25.0 … slopstopper-cli installed (0.25.0, … "pipx:slopstopper-cli" = "0.25.0"'
    assert [m.group(1) for m in _VERSION_SAMPLE.finditer(text)] == ["0.25.0"] * 3
