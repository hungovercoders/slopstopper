"""The demo repo behind `slopstopper demo`.

A tiny fixture repository, shipped as package data under
`slopstopper/data/demo/`, that the course, the demo tapes, the triage
walkthrough and the skill evals can all run slopstopper against with no
network and no clone of this repository. It is a static status page
("Lantern") with the AGENTS.md-first layout: a README, an AGENTS.md,
`CLAUDE.md` as `@AGENTS.md`, a `docs/` tree with its map, a
`.slopstopper.yml` and one page under `app/`.

Two hygiene checks fail on it on purpose, each with one finding whose
fix is the kind of edit a real repo needs:

- `hygiene:entry-files`: `README.md` is over its token budget, because
  the whole manual was pasted into it. The fix moves that content into
  `docs/` and routes it.
- `hygiene:docs-structure`: `docs/runbooks/RELEASE.md` has no route from
  the map. The fix is one row in `docs/README.md`.

`cli/tests/test_demo.py` pins both findings and their fixes, so a change
to the fixture that loses either fails the suite.

Files whose published name starts with a dot are stored without the dot
(`slopstopper.yml`, `gitignore`), so the packaged tree carries no
dotfiles; `write` renames them.
"""

from __future__ import annotations

from pathlib import Path

from slopstopper.templates import PACKAGE_DATA_DIR

DEMO_DIR = PACKAGE_DATA_DIR / "demo"
DEFAULT_OUT = "slopstopper-demo"

# Stored name → published name, for the files a repo keeps hidden.
RENAMES = {
    "slopstopper.yml": ".slopstopper.yml",
    "gitignore": ".gitignore",
}

# The deliberate findings, as `slopstopper demo` prints them: the check,
# what it reports, and the fix. test_demo.py runs each check and asserts
# the finding is the only one.
FAILURES = (
    {
        "check": "hygiene:entry-files",
        "finding": "README.md is over its token budget",
        "fix": "move the manual out of README.md into docs/ and route it from the map",
    },
    {
        "check": "hygiene:docs-structure",
        "finding": "docs/runbooks/RELEASE.md has no route",
        "fix": "add a row for it to docs/README.md (trigger, then read, then the link)",
    },
)


def files() -> list[tuple[str, Path]]:
    """Every file of the fixture as (published relative path, source path),
    in a stable order."""
    out: list[tuple[str, Path]] = []
    for source in sorted(p for p in DEMO_DIR.rglob("*") if p.is_file()):
        relative = source.relative_to(DEMO_DIR)
        name = RENAMES.get(relative.name, relative.name)
        out.append((str(relative.with_name(name)), source))
    return out


def write(dest: Path, force: bool = False) -> tuple[list[str], list[str]]:
    """Write the fixture into `dest`, creating it if needed.

    Returns the paths written and the paths skipped. A file that already
    exists is left alone unless `force` is set, so a demo repo someone
    has started editing is not wiped by a second run.
    """
    written: list[str] = []
    skipped: list[str] = []
    for published, source in files():
        target = dest / published
        if target.exists() and not force:
            skipped.append(str(target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        written.append(str(target))
    return written, skipped
