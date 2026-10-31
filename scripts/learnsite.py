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

The converter covers the markdown the lessons use and nothing more:
headings, paragraphs, bold, inline code, links, fenced code (a `sh`
fence is the site's command block, any other an output block), tables,
flat bullet and numbered lists, and `<details>` blocks whose body is
markdown. HTML comments, the harness's `<!-- learn -->` markers among
them, are dropped. A construct outside that set fails the render with
the file and line, because a page that renders wrong is worse than a
page that is not rendered.

Links: another lesson becomes that lesson's page, `README.md` the Learn
page, and a reference doc (`../hygiene/README.md`, `TEMPLATE.md`,
`EPISODES.md`) its file on GitHub; absolute links are kept.

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
from posixpath import normpath

ROOT = Path(__file__).resolve().parents[1]
LEARN = ROOT / "docs" / "learn"
SITE = ROOT / "app"
OUT = SITE / "learn"
INDEX = SITE / "learn.html"
SITEMAP = SITE / "sitemap.xml"
LLMS = SITE / "llms.txt"
BEGIN, END = "<!-- learn:begin -->", "<!-- learn:end -->"
SITE_URL = "https://slopstopper.dev/"
BLOB = "https://github.com/hungovercoders/slopstopper/blob/main/"
SERIES = "From zero to slopstopper"

_H1 = re.compile(r"^# Lesson (\d+): (.+)$")
_HEADING = re.compile(r"^(#{1,3}) (.+?)\s*$")
_BULLET = re.compile(r"^- (.*)$")
_NUMBERED = re.compile(r"^(\d+)\. (.*)$")
_FENCE = re.compile(r"^```([a-z]*)\s*$")
_TABLE_RULE = re.compile(r"^\|?(?:\s*:?-+:?\s*\|)+\s*:?-*:?\s*\|?\s*$")
_COMMENT = re.compile(r"<!--.*?-->")
_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_REL_HREF = re.compile(r'(href|src)="(?!https?:|#|mailto:)([^"]+)"')


class RenderError(Exception):
    """A construct the converter does not cover, with where it is."""


@dataclass(frozen=True)
class Lesson:
    number: int
    source: Path
    title: str

    @property
    def page(self) -> str:
        return self.source.stem + ".html"

    @property
    def heading(self) -> str:
        return f"Lesson {self.number}: {self.title}"


def lessons() -> list[Lesson]:
    found = []
    for path in sorted(LEARN.glob("[0-9]*.md")):
        first = path.read_text(encoding="utf-8").splitlines()[0]
        m = _H1.match(first)
        if not m:
            raise RenderError(f"{path.relative_to(ROOT)}:1: expected '# Lesson N: title', got {first!r}")
        found.append(Lesson(int(m.group(1)), path, m.group(2).strip()))
    return found


# ── inline markdown ──────────────────────────────────────────────


def slug(text: str) -> str:
    """A heading id the way GitHub makes one, so anchors in lesson links hold."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s+", "-", text.strip())


def rewrite_link(target: str, where: str) -> tuple[str, bool]:
    """A lesson's link target as the page needs it, and whether it leaves the site."""
    if target.startswith(("http://", "https://", "mailto:")):
        return target, True
    path, _, anchor = target.partition("#")
    anchor = f"#{anchor}" if anchor else ""
    if not path:
        return anchor, False
    if re.fullmatch(r"\d\d-[\w-]+\.md", path):
        return path[:-3] + ".html" + anchor, False
    if path == "README.md":
        return "../learn.html" + anchor, False
    if path.startswith("../") or path in ("TEMPLATE.md", "EPISODES.md"):
        return BLOB + normpath("docs/learn/" + path) + anchor, True
    raise RenderError(f"{where}: link target {target!r} is not a lesson, the syllabus or a reference doc")


def inline(text: str, where: str) -> str:
    """Escape, then mark up code spans, bold and links."""
    codes: list[str] = []

    def hold(m: re.Match) -> str:
        codes.append(f"<code>{html.escape(m.group(1), quote=False)}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = _CODE.sub(hold, text)
    text = html.escape(text, quote=False)
    text = _BOLD.sub(r"<strong>\1</strong>", text)

    def link(m: re.Match) -> str:
        href, external = rewrite_link(html.unescape(m.group(2)), where)
        rel = ' rel="noopener noreferrer"' if external else ""
        return f'<a href="{html.escape(href)}"{rel}>{m.group(1)}</a>'

    text = _LINK.sub(link, text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def split_cells(row: str) -> list[str]:
    """Table cells, with a `|` inside a code span left alone."""
    cells, cell, in_code = [], [], False
    for ch in row.strip().strip("|"):
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(ch)
    cells.append("".join(cell).strip())
    return cells


# ── block markdown ───────────────────────────────────────────────


def strip_comment(line: str, at: str) -> str:
    if "<!--" not in line:
        return line
    stripped = _COMMENT.sub("", line)
    if "<!--" in stripped:
        raise RenderError(f"{at}: a comment must open and close on one line")
    return stripped


def convert(text: str, where: str) -> str:
    """Markdown in the lessons' subset to HTML: one block at a time, each
    block reader returning its HTML and the line after it."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        at = f"{where}:{i + 1}"
        line = strip_comment(lines[i], at)
        if not line.strip():
            i += 1
            continue
        if _FENCE.match(line):
            block, i = fence_block(lines, i, at)
        elif _HEADING.match(line):
            block, i = heading_block(line, i, at)
        elif line.startswith("|") and i + 1 < len(lines) and _TABLE_RULE.match(lines[i + 1]):
            block, i = table_block(lines, i, at)
        elif _BULLET.match(line) or _NUMBERED.match(line):
            block, i = list_block(lines, i, where)
        elif line.strip() == "<details>":
            block, i = details_block(lines, i, where)
        elif line.startswith(("<", "#", ">", "* ", "+ ", "  ")):
            raise RenderError(f"{at}: {line.strip()[:60]!r} is outside the markdown the lessons use")
        else:
            block, i = paragraph_block(lines, i, at)
        out.append(block)
    return "\n".join(out)


def fence_block(lines: list[str], i: int, at: str) -> tuple[str, int]:
    lang = _FENCE.match(lines[i]).group(1)  # type: ignore[union-attr]
    body: list[str] = []
    i += 1
    while i < len(lines) and not lines[i].startswith("```"):
        body.append(lines[i])
        i += 1
    if i == len(lines):
        raise RenderError(f"{at}: unclosed code fence")
    return fence(lang, "\n".join(body)), i + 1


def heading_block(line: str, i: int, at: str) -> tuple[str, int]:
    m = _HEADING.match(line)
    level, title = len(m.group(1)), m.group(2)  # type: ignore[union-attr]
    if level == 1:
        raise RenderError(f"{at}: a second H1; the page has one, from the first line")
    return f'<h{level} id="{slug(title)}">{inline(title, at)}</h{level}>', i + 1


def table_block(lines: list[str], i: int, at: str) -> tuple[str, int]:
    head = split_cells(lines[i])
    i += 2
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append(split_cells(lines[i]))
        i += 1
    return table(head, rows, at), i


def _starts_block(line: str) -> bool:
    return bool(_BULLET.match(line) or _NUMBERED.match(line) or _HEADING.match(line))


def list_block(lines: list[str], i: int, where: str) -> tuple[str, int]:
    """A flat list; an item continues on the indented lines under it, and
    one blank line between items keeps the list going."""
    at = f"{where}:{i + 1}"
    ordered = bool(_NUMBERED.match(lines[i]))
    pattern = _NUMBERED if ordered else _BULLET
    items: list[str] = []
    while i < len(lines) and (m := pattern.match(lines[i])):
        item = [m.group(2) if ordered else m.group(1)]
        i += 1
        while i < len(lines) and lines[i].strip() and not pattern.match(lines[i]):
            if _starts_block(lines[i]):
                raise RenderError(f"{where}:{i + 1}: a list of one kind inside another is not supported")
            item.append(lines[i].strip())
            i += 1
        items.append(inline(" ".join(item), at))
        if i + 1 < len(lines) and not lines[i].strip() and pattern.match(lines[i + 1]):
            i += 1
    tag = "ol" if ordered else "ul"
    return f"<{tag}>\n" + "\n".join(f"  <li>{item}</li>" for item in items) + f"\n</{tag}>", i


def details_block(lines: list[str], i: int, where: str) -> tuple[str, int]:
    at = f"{where}:{i + 1}"
    if i + 1 >= len(lines) or not (m := re.fullmatch(r"<summary>(.+)</summary>", lines[i + 1].strip())):
        raise RenderError(f"{at}: <details> must be followed by a one-line <summary>")
    summary = m.group(1)
    depth, body = 1, []
    i += 2
    while i < len(lines):
        if lines[i].strip() == "<details>":
            depth += 1
        elif lines[i].strip() == "</details>":
            depth -= 1
            if depth == 0:
                break
        body.append(lines[i])
        i += 1
    if depth:
        raise RenderError(f"{at}: unclosed <details>")
    block = (
        '<details class="details">\n'
        f"  <summary>{inline(summary, at)}</summary>\n"
        '  <div class="details__body">\n'
        + convert("\n".join(body), where)
        + "\n  </div>\n</details>"
    )
    return block, i + 1


def _ends_paragraph(line: str) -> bool:
    return not line.strip() or bool(_FENCE.match(line)) or bool(_HEADING.match(line)) \
        or line.startswith(("|", "<details>", "- ")) or bool(_NUMBERED.match(line))


def paragraph_block(lines: list[str], i: int, at: str) -> tuple[str, int]:
    para = [strip_comment(lines[i], at).strip()]
    i += 1
    while i < len(lines) and not _ends_paragraph(lines[i]):
        para.append(_COMMENT.sub("", lines[i]).strip())
        i += 1
    return f"<p>{inline(' '.join(p for p in para if p), at)}</p>", i


def fence(lang: str, body: str) -> str:
    """A command block gets the site's copy button, which is also what
    makes the block reachable by keyboard when it scrolls sideways; any
    other block is focusable itself for the same reason. Neither is a
    landmark: a lesson has twenty of them, and axe wants landmarks named
    uniquely."""
    escaped = html.escape(body, quote=False)
    if lang == "sh":
        return f'<div class="codeblock codeblock--sh" data-copyable><pre><code>{escaped}</code></pre></div>'
    kind = {"yaml": "yaml", "python": "python"}.get(lang, "out")
    return f'<div class="codeblock codeblock--{kind}" tabindex="0"><pre><code>{escaped}</code></pre></div>'


def table(head: list[str], rows: list[list[str]], at: str) -> str:
    width = len(head)
    for row in rows:
        if len(row) != width:
            raise RenderError(f"{at}: table row has {len(row)} cells, the header {width}")
    th = "".join(f"<th>{inline(c, at)}</th>" for c in head)
    body = "\n".join("    <tr>" + "".join(f"<td>{inline(c, at)}</td>" for c in row) + "</tr>" for row in rows)
    return (
        '<div class="lesson-table-wrap" tabindex="0"><table class="lesson-table">\n'
        f"  <thead><tr>{th}</tr></thead>\n  <tbody>\n{body}\n  </tbody>\n</table></div>"
    )


# ── the page ─────────────────────────────────────────────────────


def chrome() -> tuple[str, str, str]:
    """The Learn page's head links, header and footer, with paths one
    directory up, so a lesson page is the same site as every other page."""
    page = INDEX.read_text(encoding="utf-8")

    def up(block: str) -> str:
        return _REL_HREF.sub(lambda m: f'{m.group(1)}="../{m.group(2)}"', block)

    head = "\n".join(
        line for line in page[page.index("<head>"):page.index("</head>")].splitlines()
        if re.search(r'rel="(icon|apple-touch-icon|manifest|preload)"', line)
    )
    header = page[page.index("    <header>"):page.index("    <main")]
    header = header.replace(' aria-current="page"', "")
    footer = page[page.index("    <footer>"):page.index("</body>")]
    return up(head), up(header), up(footer)


def goal(text: str) -> str:
    m = re.search(r"^\*\*Goal\.\*\*\s*(.+?)(?:\n\n|\Z)", text, re.M | re.S)
    if not m:
        raise RenderError("no '**Goal.**' paragraph to describe the page with")
    plain = re.sub(r"`([^`]*)`", r"\1", " ".join(m.group(1).split()))
    return plain if len(plain) <= 300 else plain[:297].rsplit(" ", 1)[0] + "…"


def render(lesson: Lesson, all_lessons: list[Lesson]) -> str:
    where = str(lesson.source.relative_to(ROOT))
    text = lesson.source.read_text(encoding="utf-8")
    body = text.split("\n", 1)[1]
    description = goal(body)
    try:
        content = convert(body, where)
    except RenderError as exc:
        raise RenderError(str(exc)) from None
    head_links, header, footer = chrome()
    index = all_lessons.index(lesson)
    prev = all_lessons[index - 1] if index else None
    nxt = all_lessons[index + 1] if index + 1 < len(all_lessons) else None
    title = f"{lesson.heading} | SlopStopper"
    url = f"{SITE_URL}learn/{lesson.page}"
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    nav = ['<nav class="lesson-nav" aria-label="Lessons">']
    nav.append(
        f'  <a class="lesson-nav__prev" href="{prev.page}">← Lesson {prev.number}: {esc(prev.title)}</a>' if prev
        else '  <a class="lesson-nav__prev" href="../learn.html">← The course</a>'
    )
    nav.append(
        f'  <a class="lesson-nav__next" href="{nxt.page}">Lesson {nxt.number}: {esc(nxt.title)} →</a>' if nxt
        else '  <a class="lesson-nav__next" href="../learn.html">Back to the course →</a>'
    )
    nav.append("</nav>")
    return f"""<!DOCTYPE html>
<!-- Generated from {where} by scripts/learnsite.py: edit the lesson, then `task contributing:learn:site`. -->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <meta name="theme-color" content="#FBF5EC">
    <meta name="author" content="SlopStopper">
    <!-- nosemgrep: html.security.audit.missing-integrity.missing-integrity: <link rel="canonical"> declares URL identity for SEO; it loads no subresource so SRI is structurally inapplicable -->
    <link rel="canonical" href="{url}">

    <meta property="og:type" content="article">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:site_name" content="SlopStopper">
    <meta property="og:image" content="{SITE_URL}og-image.png">
    <meta property="og:image:type" content="image/png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:image:alt" content="SlopStopper: stop the slop. Deterministic feedback for AI-driven development.">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{esc(title)}">
    <meta name="twitter:description" content="{esc(description)}">
    <meta name="twitter:image" content="{SITE_URL}og-image.png">
    <meta name="twitter:image:alt" content="SlopStopper: stop the slop. Deterministic feedback for AI-driven development.">

{head_links}
    <link rel="stylesheet" href="../shared.css">
    <link rel="stylesheet" href="../lesson.css">
</head>
<body>
{header}    <main id="main">
        <section class="hero hero--lesson">
            <span class="kicker">🎓 {SERIES} · lesson {lesson.number}</span>
            <h1>{inline(lesson.title, where)}</h1>
        </section>
        <article class="lesson">
{content}
        </article>
{chr(10).join(nav)}
        <p class="lesson-source">This page is rendered from <a href="{BLOB}{where}" rel="noopener noreferrer">{where}</a>; the commands on it run in CI on every change to the course.</p>
    </main>
{footer}    <script src="../copy.js" defer></script>
</body>
</html>
"""


# ── the sitemap and llms.txt blocks ─────────────────────────────


def with_block(text: str, block: str, where: str) -> str:
    """`text` with the part between the markers replaced by `block`."""
    begin, end = text.find(BEGIN), text.find(END)
    if begin < 0 or end < 0 or end < begin:
        raise RenderError(f"{where}: needs a `{BEGIN}` … `{END}` pair for the lesson entries")
    return text[:begin] + BEGIN + "\n" + block + "\n" + text[end:]


def sitemap_text(all_lessons: list[Lesson]) -> str:
    entries = "\n".join(
        "  <url>\n"
        f"    <loc>{SITE_URL}learn/{lesson.page}</loc>\n"
        "    <changefreq>monthly</changefreq>\n"
        "    <priority>0.6</priority>\n"
        "  </url>"
        for lesson in all_lessons
    )
    return with_block(SITEMAP.read_text(encoding="utf-8"), "  " + entries.strip(), "app/sitemap.xml")


def llms_text(all_lessons: list[Lesson]) -> str:
    entries = "\n".join(
        f"- [{lesson.heading}]({SITE_URL}learn/{lesson.page}): {goal(lesson.source.read_text(encoding='utf-8'))}"
        for lesson in all_lessons
    )
    return with_block(LLMS.read_text(encoding="utf-8"), entries, "app/llms.txt")


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
            print(f"✗ {rel} is missing; run `task contributing:learn:site`")
            problems += 1
        elif target.read_text(encoding="utf-8") != page:
            print(f"✗ {rel} is stale; run `task contributing:learn:site`")
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
            print(f"✗ {rel}'s lesson entries are stale; run `task contributing:learn:site`")
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
