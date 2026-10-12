"""The generated blocks (scripts/checktables.py) must match the registry.

The per-category check tables and the README badges are a plain function
of the registry and the installed workflows, so they are generated, and
this test fails while a committed block is stale: a new check cannot land
without its row, and a renamed badge label cannot drift from the README.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from slopstopper.checks import REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "checktables.py"


@pytest.fixture(scope="module")
def tables():
    spec = importlib.util.spec_from_file_location("checktables", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_generated_block_is_current(tables):
    stale = [
        path.relative_to(REPO_ROOT)
        for path, content in tables.render_all("hungovercoders", "slopstopper").items()
        if path.read_text(encoding="utf-8") != content
    ]
    assert not stale, f"stale generated blocks in {stale}: run `task contributing:tables`"


@pytest.mark.parametrize("category", ["hygiene", "security", "reliability"])
def test_the_category_table_lists_every_check_of_that_category(tables, category):
    table = tables.category_table(category)
    for check in REGISTRY:
        if check.split(":")[0] == category:
            assert f"| `{check}` | `task ss:{check}` |" in table
        else:
            assert f"`{check}`" not in table


def test_splice_replaces_only_what_sits_between_the_markers(tables):
    text = "before\n<!-- x:begin -->\nold\n<!-- x:end -->\nafter\n"
    assert tables.splice(text, "x", "new\n") == "before\n<!-- x:begin -->\nnew\n<!-- x:end -->\nafter\n"
    once = tables.splice(text, "x", "new\n")
    assert tables.splice(once, "x", "new\n") == once


def test_the_badges_block_has_no_heading_and_no_advert(tables):
    block = tables.badges_block("o", "r")
    assert not block.startswith("## ")
    assert "img.shields.io/badge/quality-slopstopper" not in block
    assert "ss-hygiene-complexity-check.yml" in block
