"""The demo repo behind `slopstopper demo`.

A tiny fixture repository, shipped as package data under
`slopstopper/data/demo/`, that the course, the demo tapes, the triage
walkthrough and the skill evals can all run slopstopper against with no
network and no clone of this repository. It is a static status page
("Lantern") with the AGENTS.md-first layout: a README, an AGENTS.md,
`CLAUDE.md` as `@AGENTS.md`, a `docs/` tree with its map, a
`.slopstopper.yml` and one page under `app/`.

It is deliberately a little slopped: one finding per check in
`FAILURES`, each the kind of edit a real repo needs, so the course has a
red check to read and fix for every lesson. Every other check passes or
skips on the fresh fixture, and the browser findings need the page
served (`slopstopper serve`). The one finding the fixture never carries
is a secret: a recognisably-shaped key committed here would be found by
every secrets scan of this repository's history and reported to the
vendor whose shape it borrows, so lesson 6 adds its fake private key
itself and the fixture ships `.env.example` blank.

`cli/tests/test_demo.py` pins every finding and its fix, so a change to
the fixture that loses one, or adds a second, fails the suite.

Files whose published name starts with a dot are stored without the dot
(`slopstopper.yml`, `gitignore`, `env.example`), so the packaged tree
carries no dotfiles, and the deliberately vulnerable pin is stored as
`scripts/requirements.demo` so neither this repository's dependency
review nor its Trivy run reads it as a manifest of ours; `write` renames
them, and skips anything an editor or a Python run leaves behind.
"""

from __future__ import annotations

from pathlib import Path

from slopstopper.templates import PACKAGE_DATA_DIR

DEMO_DIR = PACKAGE_DATA_DIR / "demo"
DEFAULT_OUT = "slopstopper-demo"

# Stored path → published path, for the files a repo keeps hidden. Keyed
# by the whole relative path, so a nested file that happens to share a
# name is published as is.
RENAMES = {
    "slopstopper.yml": ".slopstopper.yml",
    "gitignore": ".gitignore",
    "env.example": ".env.example",
    "scripts/requirements.demo": "scripts/requirements.txt",
}

# What an editor or a Python run can leave under data/demo/ and must never
# be written into a demo repo.
_JUNK_PARTS = {"__pycache__", ".DS_Store"}
_JUNK_SUFFIXES = ("~", ".swp", ".pyc", ".orig")

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
    {
        "check": "hygiene:docs-accuracy",
        "finding": "docs/contributing.md names `task ss:hygiene:docs`, which no Taskfile defines",
        "fix": "name the commands that exist (`slopstopper run hygiene:entry-files` and `slopstopper run hygiene:docs-structure`)",
    },
    {
        "check": "hygiene:complexity",
        "finding": "badge() in scripts/status.py is a sixteen-way if chain (CCN 17, cap 15)",
        "fix": "replace the chain with a dict lookup",
    },
    {
        "check": "security:sast",
        "finding": "scripts/status.py builds a git commit command from a string and runs it with shell=True",
        "fix": "pass the command as a list and drop shell=True",
    },
    {
        "check": "security:vulnerability:all",
        "finding": "scripts/requirements.txt pins requests 2.19.1, which carries CVE-2018-18074 (HIGH)",
        "fix": "bump the pin to the version the report's Fixed In column names, or the current release",
    },
    {
        "check": "hygiene:csp-exceptions",
        "finding": "app/_headers lets /history.html load images from https://charts.example.com and docs/security/CSP_EXCEPTIONS.md has no entry for it",
        "fix": "add the entry under ## Exceptions with all seven fields, or drop the relaxation if the page no longer needs it",
    },
    {
        "check": "reliability:accessibility",
        "finding": "the uptime chart on app/history.html is an <img> with no alt text (served: slopstopper serve)",
        "fix": "give it an alt that says what the chart shows",
    },
    {
        "check": "reliability:seo",
        "finding": "app/history.html has no <meta name=\"description\"> (served: slopstopper serve)",
        "fix": "add the one line to its <head>",
    },
    {
        "check": "reliability:sitemap",
        "finding": "app/sitemap.xml lists / but not /history.html, which the status page links to (served: slopstopper serve)",
        "fix": "add a <url> entry for it, or generate the sitemap from the page list",
    },
)


def files() -> list[tuple[str, Path]]:
    """Every file of the fixture as (published relative path, source path),
    in a stable order."""
    out: list[tuple[str, Path]] = []
    for source in sorted(p for p in DEMO_DIR.rglob("*") if p.is_file()):
        relative = source.relative_to(DEMO_DIR)
        if any(part in _JUNK_PARTS or part.startswith(".") for part in relative.parts):
            continue
        if relative.name.endswith(_JUNK_SUFFIXES):
            continue
        stored = relative.as_posix()
        out.append((RENAMES.get(stored, stored), source))
    return out


def write(dest: Path, force: bool = False) -> tuple[list[str], list[str]]:
    """Write the fixture into `dest`, creating it if needed.

    Returns the paths written and the paths skipped. A file that already
    exists is left alone unless `force` is set, so a demo repo someone
    has started editing is not wiped by a second run, and a symlink is
    never written through. A directory where a fixture file belongs, a
    file where a directory belongs, or a destination that cannot be
    written raises OSError; the caller turns that into the exit-2 message.
    """
    written: list[str] = []
    skipped: list[str] = []
    for published, source in files():
        target = dest / published
        # A symlink is never written through: that would land the file
        # wherever the link points, outside the demo. Without force it
        # counts as already there (a dangling one included); with force
        # the link itself is replaced by the file.
        if target.is_symlink():
            if not force:
                skipped.append(str(target))
                continue
            target.unlink()
        elif target.is_dir():
            raise IsADirectoryError(f"{target} is a directory, where the demo needs a file")
        elif target.exists() and not force:
            skipped.append(str(target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        written.append(str(target))
    return written, skipped
