"""The lesson pages under app/learn/, and the lesson entries in the sitemap
and llms.txt, are generated from docs/learn/ by scripts/learnsite.py and
committed, because the site has no build step. This runs the generator's
check mode, so a lesson edited without the generator, a page without a
lesson, or a change to the chrome the pages copy from app/learn.html,
fails here, in the job that runs on every pull request.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "scripts" / "learnsite.py"


def test_the_lesson_pages_match_their_lessons():
    if not GENERATOR.exists():
        pytest.skip("scripts/learnsite.py not present (running outside the repo checkout)")
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        capture_output=True, text=True, check=False, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        "the lesson pages, or the sitemap and llms.txt entries, are out of date; "
        "run `task contributing:learn:site` and commit the result:\n" + result.stdout + result.stderr
    )


def test_the_audit_page_lists_carry_every_lesson_page():
    """`.slopstopper.yml`'s pages.* lists are hand-written; the generator
    owns the sitemap and llms.txt but not these, so this keeps them in
    step with the pages under app/learn/."""
    config = (REPO_ROOT / ".slopstopper.yml").read_text(encoding="utf-8")
    pages = sorted("/learn/" + p.name for p in (REPO_ROOT / "app" / "learn").glob("*.html"))
    assert pages, "no lesson pages under app/learn/"
    for key in ("smoke", "accessibility", "seo", "broken_links"):
        line = next(l for l in config.splitlines() if l.strip().startswith(f"{key}:"))
        listed = sorted(p for p in line.split(":", 1)[1].split(",") if p.strip().startswith("/learn/"))
        assert [p.strip() for p in listed] == pages, (
            f"pages.{key} in .slopstopper.yml does not list exactly the lesson pages under app/learn/"
        )
