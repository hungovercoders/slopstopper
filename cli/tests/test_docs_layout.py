"""Guards for the documentation layout rules that prose alone kept losing.

- ``docs/index.md`` is the *only* category map. ``docs/README.md`` used to
  carry a byte-for-byte copy of the table with no check able to notice
  (both files are in ``docs_structure.ALLOWED_TOP_FILES``).
- A category README is a map, not a dumping ground: exactly one H1, with
  per-check detail extracted into sibling files that the README links.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"

_CATEGORY_ROW = re.compile(r"^\| \[`?[a-z]+/`?\]\([a-z]+/\)", re.M)
_H1 = re.compile(r"^# ", re.M)
_MD_LINK_TARGET = re.compile(r"\]\(([^)#?]+)")
_FENCE = re.compile(r"^```.*?^```", re.M | re.S)


def test_docs_readme_does_not_duplicate_the_category_table():
    text = (DOCS / "README.md").read_text(encoding="utf-8")
    assert "index.md" in text, "docs/README.md must point at docs/index.md"
    rows = _CATEGORY_ROW.findall(text)
    assert not rows, (
        "docs/README.md carries a category table again — docs/index.md is the "
        f"single map; drop these rows: {rows}"
    )


def test_docs_index_has_the_category_table():
    text = (DOCS / "index.md").read_text(encoding="utf-8")
    categories = sorted(p.name for p in DOCS.iterdir() if p.is_dir())
    rows = {m.split("[")[1].split("]")[0].strip("`/") for m in _CATEGORY_ROW.findall(text)}
    assert set(categories) <= rows, f"docs/index.md is missing rows for {sorted(set(categories) - rows)}"


@pytest.mark.parametrize("category", ["security"])
def test_category_readme_is_a_map_with_one_h1(category):
    readme = DOCS / category / "README.md"
    text = _FENCE.sub("", readme.read_text(encoding="utf-8"))  # `# comment` in bash blocks is not a heading
    assert len(_H1.findall(text)) == 1, (
        f"{readme.relative_to(REPO_ROOT)} has more than one H1 — per-check detail "
        f"belongs in a sibling docs/{category}/<CHECK>.md that the README links"
    )
    siblings = sorted(p.name for p in readme.parent.glob("*.md") if p.name != "README.md")
    linked = {Path(t).name for t in _MD_LINK_TARGET.findall(text)}
    missing = [s for s in siblings if s not in linked]
    assert not missing, f"docs/{category}/README.md does not link {missing}"
