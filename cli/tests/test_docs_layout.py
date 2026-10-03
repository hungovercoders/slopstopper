"""Guards for the documentation layout rules that prose alone kept losing.

- ``docs/index.md`` is the *only* category map. ``docs/README.md`` used to
  carry a byte-for-byte copy of the table with no check able to notice
  (both files are in ``docs_structure.ALLOWED_TOP_FILES``).
- A category README is a map, not a dumping ground: exactly one H1, with
  per-check detail extracted into sibling files. That every sibling is
  linked from a README is ``ss:hygiene:docs-structure``'s rule
  (``require_indexed_docs``), which resolves link paths — not repeated here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from slopstopper.checks import docs_structure

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
CATEGORIES = sorted(p.name for p in DOCS.iterdir() if p.is_dir())

# Same shape as docs_structure's category row, also matching a `code` span.
_CATEGORY_ROW = re.compile(r"^\| \[`?[a-z_]+/`?\]\([a-z_]+/\)", re.M)
_H1 = re.compile(r"^# ", re.M)
_FENCE = re.compile(r"^```.*?^```", re.M | re.S)

# decisions/README.md is the log AND the note template; the template's own
# H1 is what `task decisions:new` copies out, and decisions:validate checks
# for it. Its three H1s (title, log, template) are the format, not a dumping
# ground.
_EXTRA_H1_ALLOWED = {"decisions": 3}


def test_docs_readme_does_not_duplicate_the_category_table():
    text = (DOCS / "README.md").read_text(encoding="utf-8")
    assert "index.md" in text, "docs/README.md must point at docs/index.md"
    rows = _CATEGORY_ROW.findall(text)
    assert not rows, (
        "docs/README.md carries a category table again — docs/index.md is the "
        f"single map; drop these rows: {rows}"
    )


def test_docs_index_has_the_category_table():
    rows = set(docs_structure._extract_categories((DOCS / "index.md").read_text(encoding="utf-8")))
    assert set(CATEGORIES) <= rows, f"docs/index.md is missing rows for {sorted(set(CATEGORIES) - rows)}"


@pytest.mark.parametrize("category", CATEGORIES)
def test_category_readme_is_a_map_with_one_h1(category):
    readme = DOCS / category / "README.md"
    text = _FENCE.sub("", readme.read_text(encoding="utf-8"))  # `# comment` in bash blocks is not a heading
    h1s = len(_H1.findall(text))
    allowed = _EXTRA_H1_ALLOWED.get(category, 1)
    assert h1s, f"{readme.relative_to(REPO_ROOT)} has no H1 — a category README opens with its title"
    assert h1s <= allowed, (
        f"{readme.relative_to(REPO_ROOT)} has {h1s} H1s — per-check detail "
        f"belongs in a sibling docs/{category}/<CHECK>.md that the README links"
    )
