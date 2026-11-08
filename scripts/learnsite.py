#!/usr/bin/env python3
"""Render the course's lessons as pages of the site.

The lessons under docs/learn/ are markdown, read on GitHub; the site has
no build step, so the pages a reader gets at slopstopper.dev/learn/ are
written here and committed, the way the lesson tapes are. Each
`docs/learn/NN-slug.md` becomes `app/learn/NN-slug.html` in the site's
own chrome: the header, nav and footer are read from `app/learn.html`,
so the hand-copied chrome has one more copy that cannot drift, and the
page carries a title and description, the canonical, Open Graph and
Twitter tags, and links to the previous and next lesson.

The markdown converter and the page template are `scripts/sitemd.py`,
shared with `scripts/docsite.py`, which renders the reference docs the
same way. A construct outside the subset it covers fails the render with
the file and line, because a page that renders wrong is worse than a
page that is not rendered.

Links: another lesson becomes that lesson's page, `README.md` the Learn
page, and a reference doc (`../hygiene/README.md`, `TEMPLATE.md`,
`EPISODES.md`) its page under /docs/; absolute links are kept.

`app/sitemap.xml` and `app/llms.txt` each carry a block between
`<!-- learn:begin -->` and `<!-- learn:end -->` that this script owns:
one `<url>` per page, and one line per lesson under the course heading.
The rest of both files stays hand-written. `reliability:sitemap`
hard-fails on a reachable page missing from the sitemap, so the block
is what lets the Learn page link the lessons at all.

Usage:
    python scripts/learnsite.py            # (re)write every page
    python scripts/learnsite.py --check    # report stale, missing or stray pages, write nothing

`task contributing:learn:site` wraps both. Exit codes follow the suite's
contract: 0 every page written or current, 1 a page is stale, missing,
stray or cannot be rendered, 2 there are no lessons to read.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from posixpath import normpath, relpath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import docsite  # noqa: E402
import sitemd  # noqa: E402
from sitemd import BLOB, ROOT, SITE, SITE_URL, Options, Page, RenderError, plain  # noqa: E402

LEARN = ROOT / "docs" / "learn"
OUT = SITE / "learn"
INDEX = SITE / "learn.html"
SITEMAP = SITE / "sitemap.xml"
LLMS = SITE / "llms.txt"
BEGIN, END = "<!-- learn:begin -->", "<!-- learn:end -->"
SERIES = "From zero to slopstopper"
GENERATOR, TASK = "scripts/learnsite.py", "task contributing:learn:site"

_H1 = re.compile(r"^# Lesson (\d+): (.+)$")


@dataclass(frozen=True)
class Lesson:
    number: int
    source: Path
    title: str
    text: str

    @property
    def page(self) -> str:
        return self.source.stem + ".html"

    @property
    def plain_title(self) -> str:
        """The title without inline markup, for the tab, the share tags and
        the links between lessons, where no HTML can go."""
        return plain(self.title)

    @property
    def heading(self) -> str:
        return f"Lesson {self.number}: {self.plain_title}"

    @property
    def where(self) -> str:
        return str(self.source.relative_to(ROOT))

    @property
    def body(self) -> str:
        return self.text.split("\n", 1)[1]


def lessons() -> list[Lesson]:
    found = []
    for path in sorted(LEARN.glob("[0-9]*.md")):
        text = path.read_text(encoding="utf-8")
        first = text.split("\n", 1)[0]
        m = _H1.match(first)
        if not m:
            raise RenderError(f"{path.relative_to(ROOT)}:1: expected '# Lesson N: title', got {first!r}")
        found.append(Lesson(int(m.group(1)), path, m.group(2).strip(), text))
    return found


def rewrite_link(target: str) -> tuple[str, bool]:
    """A lesson's link target as the page needs it, and whether it leaves the site."""
    if target.startswith(("http://", "https://", "mailto:")):
        return target, True
    path, _, anchor = target.partition("#")
    anchor = f"#{anchor}" if anchor else ""
    if not path:
        return anchor, False
    if path == "README.md":
        return "../learn.html" + anchor, False
    href, external = sitemd.repo_link(normpath("docs/learn/" + path), anchor)
    return (href if external else relpath(href, "/learn")), external


# A `mermaid` fence is a diagram, drawn the way the docs pages draw one:
# docsite.py keeps app/assets/docs/diagrams/ in step with the lessons too,
# so a new diagram here needs `task contributing:docs:site` and then
# `task contributing:docs:diagrams` before the page shows it.
OPTIONS = Options(link=rewrite_link, diagram=lambda source: docsite.diagram_html(source, "learn"))


def goal(text: str) -> str:
    """The '**Goal.**' paragraph, as a plain-text description."""
    m = re.search(r"^\*\*Goal\.\*\*\s*(.+?)(?:\n\n|\Z)", text, re.M | re.S)
    if not m:
        raise RenderError("no '**Goal.**' paragraph to describe the page with")
    return sitemd.describe(m.group(1))


def render(lesson: Lesson, all_lessons: list[Lesson]) -> str:
    where = lesson.where
    content = sitemd.dedupe_ids(sitemd.convert(lesson.body, where, OPTIONS, base=2))
    index = all_lessons.index(lesson)
    prev = all_lessons[index - 1] if index else None
    nxt = all_lessons[index + 1] if index + 1 < len(all_lessons) else None
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    nav = ['<nav class="lesson-nav" aria-label="Lessons">']
    nav.append(
        f'  <a class="lesson-nav__prev" href="{prev.page}">← {esc(prev.heading)}</a>' if prev
        else '  <a class="lesson-nav__prev" href="../learn.html">← The course</a>'
    )
    nav.append(
        f'  <a class="lesson-nav__next" href="{nxt.page}">{esc(nxt.heading)} →</a>' if nxt
        else '  <a class="lesson-nav__next" href="../learn.html">Back to the course →</a>'
    )
    nav.append("</nav>")
    main = f"""        <section class="hero hero--lesson">
            <span class="kicker">🎓 {SERIES} · lesson {lesson.number}</span>
            <h1>{sitemd.inline(lesson.title, where, OPTIONS)}</h1>
        </section>
        <article class="lesson">
{content}
        </article>
{chr(10).join(nav)}
        <p class="lesson-source">This page is rendered from <a href="{BLOB}{where}" rel="noopener noreferrer">{where}</a>; the commands on it run in CI on every change to the course.</p>"""
    page = Page(
        source=where, generator=GENERATOR, task=TASK,
        title=lesson.heading, description=goal(lesson.body),
        path=f"/learn/{lesson.page}", og_type="article",
        chrome_from=INDEX, stylesheets=("shared.css", "lesson.css"),
    )
    return sitemd.document(page, main)


# ── the sitemap and llms.txt blocks ─────────────────────────────


def sitemap_text(all_lessons: list[Lesson]) -> str:
    entries = "\n".join(
        "  <url>\n"
        f"    <loc>{SITE_URL}learn/{lesson.page}</loc>\n"
        "    <changefreq>monthly</changefreq>\n"
        "    <priority>0.6</priority>\n"
        "  </url>"
        for lesson in all_lessons
    )
    return sitemd.with_block(SITEMAP.read_text(encoding="utf-8"), "  " + entries.strip(), BEGIN, END, "app/sitemap.xml")


def llms_text(all_lessons: list[Lesson]) -> str:
    entries = "\n".join(
        f"- [{lesson.heading}]({SITE_URL}learn/{lesson.page}): {goal(lesson.body)}"
        for lesson in all_lessons
    )
    return sitemd.with_block(LLMS.read_text(encoding="utf-8"), entries, BEGIN, END, "app/llms.txt")


# ── main ─────────────────────────────────────────────────────────


def sync_pages(found: list[Lesson], check: bool) -> int:
    """Write or check every lesson page and report strays; problems found."""
    problems = 0
    wanted = set()
    for lesson in found:
        target = OUT / lesson.page
        wanted.add(target.name)
        rel = target.relative_to(ROOT)
        try:
            page = render(lesson, found)
        except RenderError as exc:
            print(f"✗ {exc}")
            problems += 1
            continue
        if not check:
            OUT.mkdir(parents=True, exist_ok=True)
            target.write_text(page, encoding="utf-8")
            print(f"✓ {rel}")
        elif not target.exists():
            print(f"✗ {rel} is missing; run `{TASK}`")
            problems += 1
        elif target.read_text(encoding="utf-8") != page:
            print(f"✗ {rel} is stale; run `{TASK}`")
            problems += 1
        else:
            print(f"✓ {rel}")
    for stray in sorted(OUT.glob("*")) if OUT.exists() else []:
        if stray.name not in wanted:
            print(f"✗ {stray.relative_to(ROOT)} has no lesson; delete it")
            problems += 1
    return problems


def sync_blocks(found: list[Lesson], check: bool) -> int:
    """Write or check the lesson blocks in the sitemap and llms.txt; problems found."""
    problems = 0
    for path, build in ((SITEMAP, sitemap_text), (LLMS, llms_text)):
        rel = path.relative_to(ROOT)
        try:
            wanted_text = build(found)
        except RenderError as exc:
            print(f"✗ {exc}")
            problems += 1
            continue
        if path.read_text(encoding="utf-8") == wanted_text:
            print(f"✓ {rel}")
        elif check:
            print(f"✗ {rel}'s lesson entries are stale; run `{TASK}`")
            problems += 1
        else:
            path.write_text(wanted_text, encoding="utf-8")
            print(f"✓ {rel}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report stale, missing or stray pages and write nothing")
    args = parser.parse_args()
    try:
        found = lessons()
    except RenderError as exc:
        print(f"✗ {exc}")
        return 1
    if not found:
        print("learnsite: no lessons under docs/learn/", file=sys.stderr)
        return 2
    problems = sync_pages(found, args.check) + sync_blocks(found, args.check)
    if problems:
        print(f"learnsite: {problems} problem(s)")
        return 1
    print(f"learnsite: {len(found)} page(s) {'current' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
