"""The markdown the site's generated pages are rendered from.

`scripts/learnsite.py` (the course under docs/learn/) and
`scripts/docsite.py` (the reference docs under docs/) both write pages of
the site from markdown, and the site has no build step, so the pages are
committed. This module is what the two share: the converter, the site
chrome read from a hand-written page, the page template, and the one
mapping from a doc's path in the repo to its page on the site.

The converter covers the markdown the docs use and nothing more:
headings to h4, paragraphs, bold, emphasis, inline code, links and
`<https://…>` autolinks, fenced code (a `sh` or `bash` fence is the
site's command block, any other an output block), tables, blockquotes,
horizontal rules, bullet and numbered lists nested to any depth with
paragraphs and fences inside an item, and `<details>` blocks whose body
is markdown. HTML comments are dropped. A construct outside that set
fails the render with the file and line, because a page that renders
wrong is worse than a page that is not rendered.

Links are the one thing the two generators do differently (a lesson's
link to another lesson, a doc's link to a file in the repo), so each
passes its own rewriter in `Options`.
"""

from __future__ import annotations

import functools
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "app"
SITE_URL = "https://slopstopper.dev/"
REPO = "https://github.com/hungovercoders/slopstopper"
BLOB = REPO + "/blob/main/"
TREE = REPO + "/tree/main/"
OG_ALT = "SlopStopper: stop the slop. Deterministic feedback for AI-driven development."

_HEADING = re.compile(r"^(#{1,4}) (.+?)\s*$")
_BULLET = re.compile(r"^- (.*)$")
_NUMBERED = re.compile(r"^(\d+)\. (.*)$")
_FENCE = re.compile(r"^```([a-z]*)\s*$")
_TABLE_RULE = re.compile(r"^\|?(?:\s*:?-+:?\s*\|)+\s*:?-*:?\s*\|?\s*$")
_COMMENT = re.compile(r"<!--.*?-->")
_CODE = re.compile(r"`([^`]+)`")
_AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_EM = re.compile(r"(?<![\w*])\*(?=[\w(])([^*\n]+?)(?<=[\w).!?\"'])\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_REL_HREF = re.compile(r'(href|src)="(?!https?:|#|mailto:)([^"]+)"')
_LESSON_PAGE = re.compile(r"\d\d-[\w-]+\.md")

# A fence in one of these languages keeps its own class; anything else is
# an output block. `sh` and `bash` are the command block with the copy button.
COMMAND_LANGS = ("sh", "bash")
KNOWN_LANGS = ("yaml", "python", "json", "html", "css", "toml", "mermaid", "diff", "text")

Rewriter = Callable[[str], tuple[str, bool]]


class RenderError(Exception):
    """A construct the converter does not cover, with where it is."""


@dataclass(frozen=True)
class Options:
    """How one generator wants its markdown rendered.

    `link` maps a link target as written to the href the page needs and
    whether it leaves the site; it raises RenderError for a target it
    does not accept. `later_h1` says what a second H1 becomes: an error
    (a lesson has one title) or an h2 (a reference doc that carries one
    keeps its reading order; the page's h1 is its title).
    """

    link: Rewriter
    later_h1: str = "error"


# ── paths ────────────────────────────────────────────────────────


def doc_page(repo_path: str) -> str | None:
    """The site path (`/docs/hygiene/index.html`) of a markdown file under
    docs/, or None when the file is not one the site renders. A lesson is
    a page under /learn/, a README its directory's index, anything else
    its name in lower case with hyphens, so a URL reads as a path and not
    as a shout."""
    parts = repo_path.split("/")
    if parts[0] != "docs" or not parts[-1].endswith(".md") or len(parts) > 3:
        return None
    if len(parts) == 3 and parts[1] == "learn" and _LESSON_PAGE.fullmatch(parts[2]):
        return "/learn/" + parts[2][:-3] + ".html"
    name = "index" if parts[-1] == "README.md" else parts[-1][:-3].lower().replace("_", "-")
    return "/" + "/".join(parts[:-1] + [name + ".html"])


def repo_link(repo_path: str, anchor: str = "") -> tuple[str, bool]:
    """Where a link to a file in the repo goes: a doc the site renders
    becomes its page (a site-absolute path, for the caller to relativise),
    any other existing file or directory its view on GitHub. A path that
    is not in the repo is a broken link, and says so."""
    page = doc_page(repo_path)
    if page is not None and (ROOT / repo_path).is_file():
        return page + anchor, False
    if (ROOT / repo_path).is_file():
        return BLOB + repo_path + anchor, True
    if (ROOT / repo_path).is_dir():
        return TREE + repo_path + anchor, True
    raise RenderError(f"link target {repo_path!r} is not a file in the repo")


def plain(text: str) -> str:
    """Markdown inline markup stripped: backticks and bold markers."""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", re.sub(r"`([^`]*)`", r"\1", text))


def slug(text: str) -> str:
    """A heading id the way GitHub makes one, so anchors in links hold."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s+", "-", text.strip())


# ── inline markdown ──────────────────────────────────────────────


def inline(text: str, where: str, opts: Options) -> str:
    """Escape, then mark up code spans, autolinks, bold, emphasis and links."""
    held: list[str] = []

    def hold(fragment: str) -> str:
        held.append(fragment)
        return f"\x00{len(held) - 1}\x00"

    def anchor(label: str, target: str) -> str:
        try:
            href, external = opts.link(html.unescape(target))
        except RenderError as exc:
            raise RenderError(f"{where}: {exc}") from None
        rel = ' rel="noopener noreferrer"' if external else ""
        return f'<a href="{html.escape(href)}"{rel}>{label}</a>'

    text = _CODE.sub(lambda m: hold(f"<code>{html.escape(m.group(1), quote=False)}</code>"), text)
    text = _AUTOLINK.sub(lambda m: hold(anchor(html.escape(m.group(1)), m.group(1))), text)
    text = html.escape(text, quote=False)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _EM.sub(r"<em>\1</em>", text)
    text = _LINK.sub(lambda m: anchor(m.group(1), m.group(2)), text)
    return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], text)


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


def _starts_list(line: str) -> bool:
    return bool(_BULLET.match(line) or _NUMBERED.match(line))


def _starts_block(line: str) -> bool:
    """A line that opens a block other than a paragraph."""
    return (
        _starts_list(line) or bool(_HEADING.match(line)) or bool(_FENCE.match(line))
        or line.startswith(("|", "<details>", ">")) or line.rstrip() == "---"
    )


def dedupe_ids(rendered: str) -> str:
    """Heading ids made unique the way GitHub does it (`-1`, `-2`, …), so a
    doc with two "How to use" sections keeps both anchors."""
    seen: dict[str, int] = {}

    def unique(m: re.Match) -> str:
        base = m.group(1)
        n = seen.get(base, 0)
        seen[base] = n + 1
        return f'id="{base}{f"-{n}" if n else ""}"'

    return re.sub(r'id="([^"]*)"', unique, rendered)


def convert(text: str, where: str, opts: Options, base: int = 1) -> str:
    """Markdown in the site's subset to HTML: one block at a time, each
    block reader returning its HTML and the line after it. `base` is the
    file line of the first line of `text`, so an error names the real line."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        at = f"{where}:{base + i}"
        line = strip_comment(lines[i], at)
        if not line.strip():
            i += 1
            continue
        block, i = _block(lines, line, i, where, base, opts)
        out.append(block)
    return "\n".join(out)


def _block(lines: list[str], line: str, i: int, where: str, base: int, opts: Options) -> tuple[str, int]:
    """Read the block that starts at `lines[i]` (`line` is it, comments dropped)."""
    at = f"{where}:{base + i}"
    if _FENCE.match(line):
        return fence_block(lines, i, at)
    if line.startswith("```"):
        raise RenderError(f"{at}: a fence is three backticks and a language or nothing, not {line.strip()!r}")
    if _HEADING.match(line):
        return heading_block(line, i, at, opts)
    if line.startswith("|"):
        if i + 1 >= len(lines) or not _TABLE_RULE.match(lines[i + 1]):
            raise RenderError(f"{at}: a table's header row must be followed by its rule row")
        return table_block(lines, i, at, opts)
    if _starts_list(line):
        return list_block(lines, i, where, base, opts)
    if line.startswith(">"):
        return quote_block(lines, i, where, base, opts)
    if line.rstrip() == "---":
        return "<hr>", i + 1
    if line.strip() == "<details>":
        return details_block(lines, i, where, base, opts)
    if line.startswith(("<", "#", "* ", "+ ", "  ")):
        raise RenderError(f"{at}: {line.strip()[:60]!r} is outside the markdown the site renders")
    return paragraph_block(lines, i, at, opts)


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


def heading_block(line: str, i: int, at: str, opts: Options) -> tuple[str, int]:
    m = _HEADING.match(line)
    level, title = len(m.group(1)), m.group(2)  # type: ignore[union-attr]
    if level == 1:
        if opts.later_h1 != "demote":
            raise RenderError(f"{at}: a second H1; the page has one, from the first line")
        level = 2
    return f'<h{level} id="{slug(title)}">{inline(title, at, opts)}</h{level}>', i + 1


def table_block(lines: list[str], i: int, at: str, opts: Options) -> tuple[str, int]:
    head = split_cells(lines[i])
    i += 2
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append(split_cells(lines[i]))
        i += 1
    return table(head, rows, at, opts), i


def quote_block(lines: list[str], i: int, where: str, base: int, opts: Options) -> tuple[str, int]:
    """Consecutive `>` lines, their body markdown."""
    start = i
    body = []
    while i < len(lines) and lines[i].startswith(">"):
        body.append(re.sub(r"^> ?", "", lines[i]))
        i += 1
    inner = convert("\n".join(body), where, opts, base + start)
    return f"<blockquote>\n{inner}\n</blockquote>", i


def _item_end(lines: list[str], i: int, pattern: re.Pattern[str]) -> int:
    """The line after the list item whose marker is `lines[i]`: indented
    lines belong to it, as does a lazy continuation line and a blank line
    followed by an indented one."""
    i += 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].startswith(" "):
                i = j
                continue
            return i
        if not line.startswith(" ") and (pattern.match(line) or _starts_block(line) or line.startswith("<")):
            return i
        i += 1
    return i


def _item_html(first: str, body: list[str], where: str, base: int, opts: Options) -> str:
    """One item: its first paragraph (the marker line plus any lazy or
    indented continuation lines), then its nested blocks, de-indented."""
    indents = [len(l) - len(l.lstrip()) for l in body if l.strip()]
    depth = min(indents) if indents else 0
    body = [l[depth:] if l.strip() else "" for l in body]
    para = [first]
    k = 0
    while k < len(body) and body[k].strip() and not _starts_block(body[k]):
        para.append(body[k].strip())
        k += 1
    nested = convert("\n".join(body[k:]), where, opts, base + k)
    at = f"{where}:{base - 1}"
    return f"<li>{inline(' '.join(para), at, opts)}" + (f"\n{nested}\n</li>" if nested else "</li>")


def list_block(lines: list[str], i: int, where: str, base: int, opts: Options) -> tuple[str, int]:
    """A list of one kind; an item's indented lines are its own markdown,
    so a nested list, a paragraph or a fence inside an item renders in
    place. One blank line between items keeps the list going."""
    ordered = bool(_NUMBERED.match(lines[i]))
    pattern = _NUMBERED if ordered else _BULLET
    start = f' start="{m.group(1)}"' if ordered and (m := _NUMBERED.match(lines[i])).group(1) != "1" else ""
    items: list[str] = []
    while i < len(lines) and (m := pattern.match(lines[i])):
        end = _item_end(lines, i, pattern)
        first = m.group(2) if ordered else m.group(1)
        items.append(_item_html(first, lines[i + 1:end], where, base + i + 1, opts))
        i = end
        if i + 1 < len(lines) and not lines[i].strip() and pattern.match(lines[i + 1]):
            i += 1
    tag = "ol" if ordered else "ul"
    return f"<{tag}{start}>\n" + "\n".join(f"  {item}" for item in items) + f"\n</{tag}>", i


def details_block(lines: list[str], i: int, where: str, base: int, opts: Options) -> tuple[str, int]:
    at = f"{where}:{base + i}"
    if i + 1 >= len(lines) or not (m := re.fullmatch(r"<summary>(.+)</summary>", lines[i + 1].strip())):
        raise RenderError(f"{at}: <details> must be followed by a one-line <summary>")
    summary = m.group(1)
    depth, body = 1, []
    i += 2
    body_base = base + i
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
        f"  <summary>{inline(summary, at, opts)}</summary>\n"
        '  <div class="details__body">\n'
        + convert("\n".join(body), where, opts, body_base)
        + "\n  </div>\n</details>"
    )
    return block, i + 1


def _ends_paragraph(line: str) -> bool:
    return not line.strip() or _starts_block(line)


def paragraph_block(lines: list[str], i: int, at: str, opts: Options) -> tuple[str, int]:
    para = [strip_comment(lines[i], at).strip()]
    i += 1
    while i < len(lines) and not _ends_paragraph(lines[i]):
        para.append(_COMMENT.sub("", lines[i]).strip())
        i += 1
    return f"<p>{inline(' '.join(p for p in para if p), at, opts)}</p>", i


def fence(lang: str, body: str) -> str:
    """A command block gets the site's copy button, which is also what
    makes the block reachable by keyboard when it scrolls sideways; any
    other block is focusable itself for the same reason. Neither is a
    landmark: a lesson has twenty of them, and axe wants landmarks named
    uniquely."""
    escaped = html.escape(body, quote=False)
    if lang in COMMAND_LANGS:
        return f'<div class="codeblock codeblock--sh" data-copyable><pre><code>{escaped}</code></pre></div>'
    kind = lang if lang in KNOWN_LANGS else "out"
    return f'<div class="codeblock codeblock--{kind}" tabindex="0"><pre><code>{escaped}</code></pre></div>'


def table(head: list[str], rows: list[list[str]], at: str, opts: Options) -> str:
    width = len(head)
    for row in rows:
        if len(row) != width:
            raise RenderError(f"{at}: table row has {len(row)} cells, the header {width}")
    th = "".join(f"<th>{inline(c, at, opts)}</th>" for c in head)
    body = "\n".join("    <tr>" + "".join(f"<td>{inline(c, at, opts)}</td>" for c in row) + "</tr>" for row in rows)
    return (
        '<div class="lesson-table-wrap" tabindex="0"><table class="lesson-table">\n'
        f"  <thead><tr>{th}</tr></thead>\n  <tbody>\n{body}\n  </tbody>\n</table></div>"
    )


# ── the page ─────────────────────────────────────────────────────


@functools.lru_cache(maxsize=4)
def chrome(index: Path, depth: int) -> tuple[str, str, str]:
    """A hand-written page's head links, its skip link and header, and its
    footer, with relative paths lifted `depth` directories up, so a
    generated page is the same site as every other page. Read once per run."""
    page = index.read_text(encoding="utf-8")
    rel = index.relative_to(ROOT)
    up_path = "../" * depth

    def up(block: str) -> str:
        return _REL_HREF.sub(lambda m: f'{m.group(1)}="{up_path}{m.group(2)}"', block)

    def between(start: str, end: str, what: str) -> str:
        try:
            begin = page.index(start)
            return page[begin:page.index(end, begin) + (len(end) if end.startswith("</") else 0)]
        except ValueError:
            raise RenderError(f"{rel}: no {what} between {start.strip()!r} and {end.strip()!r}") from None

    head = "\n".join(
        line for line in between("<head>", "</head>", "head").splitlines()
        if re.search(r'rel="(icon|apple-touch-icon|manifest|preload)"', line)
    )
    header = between('    <a href="#main"', "    <main", "skip link and header").replace(' aria-current="page"', "")
    footer = between("    <footer>", "</footer>", "footer") + "\n"
    return up(head), up(header), up(footer)


@dataclass(frozen=True)
class Page:
    """What a generated page needs besides its main content."""

    source: str          # repo-relative markdown file, for the generated-from comment
    generator: str       # `scripts/learnsite.py`, and the task that runs it
    task: str
    title: str           # the tab title, plain text, without the site suffix
    description: str     # plain text, for the meta and share tags
    path: str            # site path, `/learn/01-install.html`
    og_type: str         # `article` or `website`
    chrome_from: Path    # the hand-written page the header and footer are read from
    stylesheets: tuple[str, ...]


def document(page: Page, main: str) -> str:
    """The whole HTML page: the shared head, the chrome and `main`'s content."""
    depth = page.path.count("/") - 1
    up_path = "../" * depth
    head_links, header, footer = chrome(page.chrome_from, depth)
    esc = functools.partial(html.escape, quote=True)
    title = f"{page.title} | SlopStopper"
    url = SITE_URL + page.path.lstrip("/")
    sheets = "\n".join(f'    <link rel="stylesheet" href="{up_path}{s}">' for s in page.stylesheets)
    return f"""<!DOCTYPE html>
<!-- Generated from {page.source} by {page.generator}: edit the source, then `{page.task}`. -->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(page.description)}">
    <meta name="theme-color" media="(prefers-color-scheme: light)" content="#FBF5EC">
    <meta name="theme-color" media="(prefers-color-scheme: dark)" content="#1B1612">
    <meta name="author" content="SlopStopper">
    <!-- nosemgrep: html.security.audit.missing-integrity.missing-integrity: <link rel="canonical"> declares URL identity for SEO; it loads no subresource so SRI is structurally inapplicable -->
    <link rel="canonical" href="{url}">

    <meta property="og:type" content="{page.og_type}">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(page.description)}">
    <meta property="og:site_name" content="SlopStopper">
    <meta property="og:image" content="{SITE_URL}og-image.png">
    <meta property="og:image:type" content="image/png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:image:alt" content="{OG_ALT}">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{esc(title)}">
    <meta name="twitter:description" content="{esc(page.description)}">
    <meta name="twitter:image" content="{SITE_URL}og-image.png">
    <meta name="twitter:image:alt" content="{OG_ALT}">

    <script src="{up_path}theme.js"></script>
{head_links}
{sheets}
</head>
<body>
{header}    <main id="main">
{main}
    </main>
{footer}    <script src="{up_path}copy.js" defer></script>
</body>
</html>
"""


def with_block(text: str, block: str, begin: str, end: str, where: str) -> str:
    """`text` with the part between the markers replaced by `block`."""
    b, e = text.find(begin), text.find(end)
    if b < 0 or e < 0 or e < b:
        raise RenderError(f"{where}: needs a `{begin}` … `{end}` pair for the generated entries")
    return text[:b] + begin + "\n" + block + "\n" + text[e:]


def describe(text: str, limit: int = 300) -> str:
    """Plain text for a description, cut at a word before `limit`."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", " ".join(text.split()))
    text = plain(text).replace("*", "")
    return text if len(text) <= limit else text[:limit - 3].rsplit(" ", 1)[0] + "…"
