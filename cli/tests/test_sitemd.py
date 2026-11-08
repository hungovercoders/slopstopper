"""The markdown converter behind the site's generated pages, scripts/sitemd.py.

The pages are committed, so a construct the converter mishandles ships
as a wrong page unless the converter refuses it; these tests pin what it
renders and what it refuses. The script is loaded from the repo checkout,
the way test_learn_site.py runs the generators.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sitemd.py"


@pytest.fixture(scope="module")
def sitemd():
    if not SCRIPT.exists():
        pytest.skip("scripts/sitemd.py not present (running outside the repo checkout)")
    sys.path.insert(0, str(SCRIPT.parent))
    return importlib.import_module("sitemd")


@pytest.fixture
def convert(sitemd):
    """Render markdown with a rewriter that keeps every link as written."""
    opts = sitemd.Options(link=lambda target: (target, target.startswith("http")))
    return lambda text: sitemd.convert(text, "test.md", opts)


def test_a_comment_inside_a_code_span_is_text(convert):
    html = convert("so a `<!-- Cloudflare -->` or a `data-host=` does not count")
    assert "<code>&lt;!-- Cloudflare --&gt;</code>" in html
    assert "<code>data-host=</code>" in html


def test_a_comment_outside_code_is_dropped(convert):
    assert convert("kept <!-- dropped --> text") == "<p>kept  text</p>"
    assert convert("<!-- only a comment -->\n\nnext") == "<p>next</p>"


def test_list_items_and_cells_treat_comments_like_paragraphs(convert):
    assert "<code>&lt;!-- x --&gt;</code>" in convert("- a `<!-- x -->` marker")
    assert "<code>&lt;!-- x --&gt;</code>" in convert("| a |\n| - |\n| `<!-- x -->` |")


def test_a_url_with_parentheses_is_whole(convert):
    html = convert("[w](https://en.wikipedia.org/wiki/Foo_(bar)) after")
    assert 'href="https://en.wikipedia.org/wiki/Foo_(bar)"' in html
    assert ">w</a> after" in html


def test_an_autolink_may_start_a_paragraph(convert):
    assert convert("<https://example.com> is here").startswith('<p><a href="https://example.com"')


@pytest.mark.parametrize(
    "text, reason",
    [
        ("![alt](img.png)", "images"),
        ('[x](https://a.b "title")', "link title"),
        ("press <kbd>Ctrl</kbd> now", "inline HTML"),
        ("a <!-- open comment", "open and close"),
    ],
)
def test_unsupported_markdown_is_refused_not_rendered(sitemd, convert, text, reason):
    with pytest.raises(sitemd.RenderError, match=reason):
        convert(text)


def test_a_directory_link_lands_on_its_readme_page(sitemd):
    href, external = sitemd.repo_link("docs/hygiene")
    assert (href, external) == ("/docs/hygiene/index.html", False)
    href, external = sitemd.repo_link("cli/slopstopper/checks")
    assert external and href.endswith("/tree/main/cli/slopstopper/checks")
