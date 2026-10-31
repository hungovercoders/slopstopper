"""The site's Learn page lists the course, and the course's syllabus is
where lessons are added. Nothing renders one from the other (the site has
no build step), so this test does the comparing: the page must list
exactly the syllabus's lessons, in order, with the same titles, each
linking to its page on GitHub. It also pins the one thing a new page most
often breaks, the main nav, which is copied into every page by hand.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SYLLABUS = REPO_ROOT / "docs/learn/README.md"
PAGE = REPO_ROOT / "app/learn.html"
LESSON_BASE = "https://github.com/hungovercoders/slopstopper/blob/main/docs/learn/"

_SYLLABUS_ROW = re.compile(r"^\| (\d+) \| \[([^\]]+)\]\(([^)]+\.md)\) \|", re.M)
_PAGE_LESSON = re.compile(
    r'<li class="lesson">.*?<span class="lesson__num"[^>]*>(\d+)</span>.*?'
    r'<a href="([^"]+)"[^>]*><span class="visually-hidden">Lesson \d+: </span>(.*?)</a>',
    re.S,
)
_MAIN_NAV = re.compile(r'<nav aria-label="Main">(.*?)</nav>', re.S)
_NAV_LINK = re.compile(r'<a href="([^"]+)" id="(nav-[a-z]+)"( aria-current="page")?>([^<]+)</a>')


def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"{path.relative_to(REPO_ROOT)} not present (running outside the repo checkout)")
    return path.read_text(encoding="utf-8")


def _plain(fragment: str) -> str:
    """Page title HTML (with <code> for backticks) back to syllabus text."""
    return html.unescape(re.sub(r"</?code>", "`", fragment))


def test_the_page_lists_every_syllabus_lesson_in_order():
    syllabus = [(int(n), title, LESSON_BASE + file) for n, title, file in _SYLLABUS_ROW.findall(_read(SYLLABUS))]
    page = [(int(n), _plain(title), href) for n, href, title in _PAGE_LESSON.findall(_read(PAGE))]
    assert syllabus, "no linked lessons found in docs/learn/README.md"
    assert page == syllabus, (
        "app/learn.html's lesson list differs from docs/learn/README.md's syllabus; "
        "add, rename or reorder the lesson on the page to match"
    )


def test_every_linked_lesson_exists():
    for _, _, file in _SYLLABUS_ROW.findall(_read(SYLLABUS)):
        assert (SYLLABUS.parent / file).is_file(), f"the syllabus links docs/learn/{file}, which does not exist"


def _nav(page: Path) -> tuple[list[tuple[str, str, str]], list[str]]:
    match = _MAIN_NAV.search(_read(page))
    assert match, f"{page.name} has no main nav"
    links = _NAV_LINK.findall(match.group(1))
    return [(href, nav_id, label) for href, nav_id, _, label in links], [
        href for href, _, current, _ in links if current
    ]


def test_every_page_carries_the_same_main_nav():
    pages = sorted((REPO_ROOT / "app").glob("*.html"))
    expected, _ = _nav(REPO_ROOT / "app/index.html")
    assert ("learn.html", "nav-learn", "Learn") in expected
    for page in pages:
        links, current = _nav(page)
        assert links == expected, f"{page.name}'s main nav differs from index.html's"
        in_nav = page.name in {href for href, _, _ in links}
        assert current == ([page.name] if in_nav else []), (
            f"{page.name} must mark itself, and only itself, with aria-current"
        )
