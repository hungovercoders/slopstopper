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
