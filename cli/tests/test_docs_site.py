"""The doc pages under app/docs/, the section list on app/docs.html and the
doc entries in the sitemap and llms.txt are generated from docs/ by
scripts/docsite.py and committed, because the site has no build step.
This runs the generator's check mode, so a doc edited without the
generator, a page without a doc, a doc with a construct the converter
does not cover or a dead relative link, or a change to the chrome the
pages copy from app/docs.html, fails here, in the job that runs on every
pull request.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "scripts" / "docsite.py"
DOC_PAGES = REPO_ROOT / "app" / "docs"


def test_the_doc_pages_match_their_docs():
    if not GENERATOR.exists():
        pytest.skip("scripts/docsite.py not present (running outside the repo checkout)")
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        capture_output=True, text=True, check=False, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        "the doc pages, or the Docs page, sitemap and llms.txt entries, are out of date; "
        "run `task contributing:docs:site` and commit the result:\n" + result.stdout + result.stderr
    )


def test_the_audit_page_lists_carry_every_doc_page():
    """`.slopstopper.yml`'s pages.* lists are hand-written; the generator
    owns the sitemap and llms.txt but not these, so this keeps them in
    step with the Docs page and the pages under app/docs/."""
    if not DOC_PAGES.exists():
        pytest.skip("app/docs/ not present (running outside the repo checkout)")
    config = (REPO_ROOT / ".slopstopper.yml").read_text(encoding="utf-8")
    pages = sorted(["/docs.html"] + ["/" + p.relative_to(REPO_ROOT / "app").as_posix() for p in DOC_PAGES.rglob("*.html")])
    assert len(pages) > 1, "no doc pages under app/docs/"
    for key in ("smoke", "accessibility", "seo", "broken_links"):
        line = next(l for l in config.splitlines() if l.strip().startswith(f"{key}:"))
        listed = sorted(p.strip() for p in line.split(":", 1)[1].split(",") if p.strip().startswith("/docs"))
        assert listed == pages, (
            f"pages.{key} in .slopstopper.yml does not list exactly /docs.html and the doc pages under app/docs/"
        )


def test_every_doc_page_the_docs_page_links_exists():
    """The section list is generated, but the three doors above it and the
    agent section are hand-written; every page they link must exist."""
    page = REPO_ROOT / "app" / "docs.html"
    if not page.exists():
        pytest.skip("app/docs.html not present (running outside the repo checkout)")
    import re

    for href in re.findall(r'href="(docs/[^"#]+)', page.read_text(encoding="utf-8")):
        assert (REPO_ROOT / "app" / href).is_file(), f"app/docs.html links {href}, which does not exist; run `task contributing:docs:site`"
