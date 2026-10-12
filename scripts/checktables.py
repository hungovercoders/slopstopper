#!/usr/bin/env python3
"""Regenerate the check tables and the README badges from the registry.

    task contributing:tables               # rewrite the generated blocks
    task contributing:tables -- --check    # exit 1 and name any stale file

A new or renamed check is registered in many places by hand; the ones
that are a plain function of the registry should not be. This script
writes, between marker comments, the block each file carries:

  docs/hygiene/README.md, docs/security/README.md,
  docs/reliability/README.md   <!-- checks:begin --> … <!-- checks:end -->
      one row per check in that category: the check, how to run it, the
      workflow that fronts it, and the first line of its docstring (what
      `slopstopper checks list` prints)
  README.md                    <!-- badges:begin --> … <!-- badges:end -->
      the badge block `slopstopper badges` generates for the workflows in
      .github/workflows/, so the README shows every installed check

Everything outside the markers is hand-written and left alone.
`cli/tests/test_check_tables.py` fails while a block is stale, so a
check cannot land without its row.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

from slopstopper import badges, profiles
from slopstopper.checks import REGISTRY
from slopstopper.cli import _check_summary

ROOT = Path(__file__).resolve().parent.parent

CATEGORY_PAGES = {
    "hygiene": ROOT / "docs/hygiene/README.md",
    "security": ROOT / "docs/security/README.md",
    "reliability": ROOT / "docs/reliability/README.md",
}
README = ROOT / "README.md"

# slopstopper.dev's own coordinates; `--owner`/`--repo` override them for
# a fork, and the test passes them explicitly.
OWNER, REPO = "hungovercoders", "slopstopper"


def category_table(category: str) -> str:
    """The markdown table for every registry check in `category`."""
    rows = [
        "| Check | Run it | Workflow | What it does |",
        "| ----- | ------ | -------- | ------------ |",
    ]
    for check in sorted(REGISTRY):
        if check.split(":")[0] != category:
            continue
        workflow = profiles.workflow_for(check) or ""
        rows.append(
            f"| `{check}` | `task ss:{check}` | `{workflow}` | {_check_summary(check)} |"
        )
    return "\n".join(rows) + "\n"


def badges_block(owner: str = OWNER, repo: str = REPO) -> str:
    """The README's badge groups, without the generator's own heading."""
    # The generator lists .github/workflows/ relative to the working
    # directory; pin it to the repository so the test can run from cli/.
    with contextlib.chdir(ROOT):
        block = badges.generate(owner=owner, repo=repo, no_advert=True)
    heading = "## Pipeline status\n\n"
    return block[len(heading):] if block.startswith(heading) else block


def splice(text: str, name: str, body: str) -> str:
    """Replace what sits between `<!-- name:begin -->` and `<!-- name:end -->`."""
    begin, end = f"<!-- {name}:begin -->", f"<!-- {name}:end -->"
    start = text.index(begin) + len(begin)
    stop = text.index(end)
    return f"{text[:start]}\n{body}{text[stop:]}"


def render_all(owner: str = OWNER, repo: str = REPO) -> dict[Path, str]:
    """Each generated file's full new content, keyed by path."""
    out = {}
    for category, path in CATEGORY_PAGES.items():
        out[path] = splice(path.read_text(encoding="utf-8"), "checks", category_table(category))
    out[README] = splice(README.read_text(encoding="utf-8"), "badges", badges_block(owner, repo))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report stale files and exit 1 instead of writing")
    parser.add_argument("--owner", default=OWNER)
    parser.add_argument("--repo", default=REPO)
    args = parser.parse_args()
    stale = []
    for path, content in render_all(args.owner, args.repo).items():
        if path.read_text(encoding="utf-8") == content:
            continue
        stale.append(path)
        if not args.check:
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if args.check and stale:
        names = ", ".join(str(p.relative_to(ROOT)) for p in stale)
        print(f"stale: {names}. Run `task contributing:tables`.", file=sys.stderr)
        return 1
    if not stale:
        print("every generated block is current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
