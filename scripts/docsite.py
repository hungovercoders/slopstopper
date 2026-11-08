#!/usr/bin/env python3
"""Render the reference docs as pages of the site.

The docs under docs/ are markdown, routed from AGENTS.md and read on
GitHub; a visitor to slopstopper.dev who followed a "learn more" link
used to land on GitHub too. The site has no build step, so the pages are
written here and committed, the way the lesson pages are. Each
`docs/<dir>/<NAME>.md` the site renders becomes
`app/docs/<dir>/<name>.html` (a README its directory's `index.html`), in
the site's own chrome read from `app/docs.html`, with a breadcrumb and
the other docs of its section.

The site is for people using slopstopper, so it renders the sections an
adopter reads (`sitemd.SITE_SECTIONS`: the checks, the runbooks, the
architecture they meet, support) and nothing about working on this
repository: contributing, deployment, the site, the decisions, the
course's authoring notes, the docs map and the release runbook
(`sitemd.OFF_SITE`) stay on GitHub, and a link to one of them from a
rendered page goes there. The lessons under docs/learn/ are the course's
pages under /learn/ (`scripts/learnsite.py`).

A `mermaid` fence becomes a diagram: the page shows an SVG per theme
from `app/assets/docs/diagrams/<digest>-{light,dark}.svg`, with the
Mermaid source folded beneath it for readers and screen readers, where
`<digest>` is the first twelve hex digits of the source's SHA-256. This
script writes the source beside them as `<digest>.mmd` and reports a
diagram whose SVGs are missing; `scripts/diagrams.js` renders them
(`task contributing:docs:diagrams`), because the site's CSP allows no
script or inline style, so a diagram cannot render in the browser.
The lessons' fences (scripts/learnsite.py) are drawn the same way, and
this script renders the lessons too when it syncs the directory, so one
directory holds every diagram on the site.

`scripts/sitemd.py` holds the converter and the page template, shared
with the course. A construct outside the markdown it covers fails the
render with the file and line. A relative link to another doc becomes
that doc's page, to a lesson that lesson's page, to any other file in
the repo its view on GitHub; a link to a file that is not there fails
the render, so the pages never carry a dead link.

The Docs page lists every section, its index's opening line and its
other docs, between `<!-- docs:begin -->` and `<!-- docs:end -->`;
`app/sitemap.xml` and `app/llms.txt` carry one entry per page between
the same markers. This script owns those blocks and nothing else in the
three files. `reliability:sitemap` hard-fails
on a reachable page missing from the sitemap, so the block is what lets
the site link the docs at all.

Usage:
    python scripts/docsite.py            # (re)write every page
    python scripts/docsite.py --check    # report stale, missing or stray pages, write nothing

`task contributing:docs:site` wraps both. Exit codes follow the suite's
contract: 0 every page written or current, 1 a page is stale, missing,
stray or cannot be rendered, 2 there are no docs to read.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from posixpath import dirname, normpath, relpath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sitemd  # noqa: E402
from sitemd import DIAGRAMS, DIAGRAMS_DIR, ROOT, SITE, SITE_URL, THEMES, Options, Page, RenderError, diagram_html, plain  # noqa: E402

DOCS = ROOT / "docs"
OUT = SITE / "docs"
INDEX = SITE / "docs.html"
SITEMAP = SITE / "sitemap.xml"
LLMS = SITE / "llms.txt"
BEGIN, END = "<!-- docs:begin -->", "<!-- docs:end -->"
GENERATOR, TASK = "scripts/docsite.py", "task contributing:docs:site"
DIAGRAMS_TASK = "task contributing:docs:diagrams"


# The name each rendered section (sitemd.SITE_SECTIONS) shows in the
# kicker, the breadcrumb and the Docs page.
SECTIONS = {
    "runbooks": "Runbooks",
    "hygiene": "Hygiene",
    "security": "Security",
    "reliability": "Reliability",
    "architecture": "Architecture",
    "support": "Support",
}
CURRENT = ' aria-current="page"'


def section_name(key: str) -> str:
    return SECTIONS[key]

_H1 = re.compile(r"^# (.+?)\s*$")


@dataclass(frozen=True)
class Doc:
    source: Path
    title: str
    text: str

    @property
    def where(self) -> str:
        return str(self.source.relative_to(ROOT))

    @property
    def path(self) -> str:
        """The page's site path, `/docs/hygiene/index.html`."""
        return sitemd.doc_page(self.where)  # type: ignore[return-value]

    @property
    def section(self) -> str:
        """The directory under docs/."""
        return self.where.split("/")[1]

    @property
    def is_index(self) -> bool:
        return self.source.name == "README.md"

    @property
    def plain_title(self) -> str:
        return plain(self.title)

    @property
    def body(self) -> str:
        return self.text.split("\n", 1)[1] if "\n" in self.text else ""

    @property
    def description(self) -> str:
        return sitemd.describe(intro(self.body, self.where))


def intro(body: str, where: str) -> str:
    """The doc's first paragraph, for its description: headings, comments
    and blank lines before it are skipped, and a blockquote counts."""
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("<!--"):
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
        elif lines[i].strip() and not lines[i].startswith("#"):
            break
        i += 1
    para = []
    while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "```", "|", "<", "- ")):
        para.append(re.sub(r"^> ?", "", lines[i]).strip())
        i += 1
    if not para:
        raise RenderError(f"{where}: needs an opening paragraph to describe the page with")
    return " ".join(para)


def docs() -> list[Doc]:
    """Every doc the site renders, by section order, index first, then name."""
    if set(sitemd.SITE_SECTIONS) != set(SECTIONS):
        raise RenderError("docsite.SECTIONS and sitemd.SITE_SECTIONS name different sections")
    found = []
    for key in SECTIONS:
        if not (DOCS / key / "README.md").is_file():
            raise RenderError(f"docs/{key}/README.md is missing; every section in docsite.SECTIONS needs its index")
        for path in sorted((DOCS / key).rglob("*.md")):
            rel = path.relative_to(ROOT).as_posix()
            if rel in sitemd.OFF_SITE:
                continue
            if sitemd.doc_page(rel) is None:
                raise RenderError(f"{rel}: deeper than docs/<dir>/, which the site does not render")
            text = path.read_text(encoding="utf-8")
            m = _H1.match(text.split("\n", 1)[0])
            if not m:
                raise RenderError(f"{rel}:1: expected '# Title' on the first line")
            found.append(Doc(path, m.group(1), text))
    return sorted(found, key=lambda d: (list(SECTIONS).index(d.section), not d.is_index, d.source.name.lower()))


# ── links ────────────────────────────────────────────────────────


def rewriter(doc: Doc) -> sitemd.Rewriter:
    """The link rewriter for one doc: relative targets resolve against its
    directory, and a site page comes back relative to the doc's page."""
    here = dirname(doc.where)
    page_dir = dirname(doc.path)

    def rewrite(target: str) -> tuple[str, bool]:
        if target.startswith(("http://", "https://", "mailto:")):
            return target, True
        path, _, anchor = target.partition("#")
        anchor = f"#{anchor}" if anchor else ""
        if not path:
            return anchor, False
        if path.startswith("/"):
            raise RenderError(f"link target {target!r} is root-absolute; make it relative to the doc")
        repo_path = normpath(f"{here}/{path}")
        if repo_path.startswith(".."):
            raise RenderError(f"link target {target!r} leaves the repository")
        href, external = sitemd.repo_link(repo_path, anchor)
        return (href if external else relpath(href, page_dir)), external

    return rewrite


def options(doc: Doc) -> Options:
    page_dir = dirname(doc.path)
    return Options(link=rewriter(doc), later_h1="demote", diagram=lambda source: diagram_html(source, page_dir))


# ── diagrams ─────────────────────────────────────────────────────


def register_lesson_diagrams() -> None:
    """The lessons (scripts/learnsite.py) draw their `mermaid` fences through
    sitemd.diagram_html too. Render them the way learnsite does, so exactly
    the fences a lesson page shows are registered, and their sources are
    not strays."""
    import learnsite  # noqa: PLC0415 (learnsite imports sitemd, never this module)

    for lesson in learnsite.lessons():
        sitemd.convert(lesson.body, lesson.where, learnsite.OPTIONS, base=2)


def sync_diagrams(check: bool) -> int:
    """Write or check the diagram sources, report SVGs still to render and
    strays from diagrams that no longer exist; problems found."""
    problems = 0
    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    for digest, source in sorted(DIAGRAMS.items()):
        mmd = DIAGRAMS_DIR / f"{digest}.mmd"
        if not mmd.is_file() or mmd.read_text(encoding="utf-8") != source + "\n":
            if check:
                print(f"✗ {mmd.relative_to(ROOT)} is missing or stale; run `{TASK}`")
                problems += 1
            else:
                mmd.write_text(source + "\n", encoding="utf-8")
        missing = [t for t in THEMES if not (DIAGRAMS_DIR / f"{digest}-{t}.svg").is_file()]
        if missing:
            print(f"✗ {DIAGRAMS_DIR.relative_to(ROOT)}/{digest}-{{{','.join(missing)}}}.svg not rendered; run `{DIAGRAMS_TASK}`")
            problems += 1
    for stray in sorted(DIAGRAMS_DIR.iterdir()):
        if stray.name.split("-")[0].split(".")[0] in DIAGRAMS:
            continue
        if check:
            print(f"✗ {stray.relative_to(ROOT)} belongs to no diagram; run `{TASK}`")
            problems += 1
        else:
            stray.unlink()
            print(f"✓ removed {stray.relative_to(ROOT)}")
    return problems


# ── the page ─────────────────────────────────────────────────────


def _crumbs(doc: Doc, esc) -> str:
    rel = lambda p: relpath(p, dirname(doc.path))  # noqa: E731
    items = [f'<li><a href="{rel("/docs.html")}">Docs</a></li>']
    if doc.is_index:
        items.append(f'<li aria-current="page">{esc(section_name(doc.section))}</li>')
    else:
        items.append(f'<li><a href="index.html">{esc(section_name(doc.section))}</a></li>')
        items.append(f'<li aria-current="page">{esc(doc.plain_title)}</li>')
    return '<nav class="doc-crumbs" aria-label="Breadcrumb"><ol>' + "".join(items) + "</ol></nav>"


def _siblings(doc: Doc, all_docs: list[Doc], esc) -> str:
    """The pages of the doc's section, the doc itself marked current."""
    rel = lambda p: relpath(p, dirname(doc.path))  # noqa: E731
    heading = f"In {section_name(doc.section)}"
    items = "\n".join(
        f'    <li><a href="{rel(d.path)}"{CURRENT if d is doc else ""}>{esc(d.plain_title)}</a></li>'
        for d in all_docs if d.section == doc.section
    )
    return f'<nav class="doc-siblings" aria-label="{esc(heading)}">\n  <h2>{esc(heading)}</h2>\n  <ul>\n{items}\n  </ul>\n</nav>'


def render(doc: Doc, all_docs: list[Doc]) -> str:
    opts = options(doc)
    where = doc.where
    content = sitemd.dedupe_ids(sitemd.convert(doc.body, where, opts, base=2))
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    section = section_name(doc.section)
    main = f"""        <section class="hero hero--lesson hero--doc">
            <span class="kicker">📚 Docs · {esc(section)}</span>
            <h1>{sitemd.inline(doc.title, where, opts)}</h1>
        </section>
        {_crumbs(doc, esc)}
        <article class="lesson doc">
{content}
        </article>
{_siblings(doc, all_docs, esc)}"""
    page = Page(
        source=where, generator=GENERATOR, task=TASK,
        title=f"{doc.plain_title} · {section}",
        description=doc.description, path=doc.path, og_type="article",
        chrome_from=INDEX, stylesheets=("shared.css", "lesson.css", "docs.css"),
    )
    return sitemd.document(page, main)


# ── the Docs page, sitemap and llms.txt blocks ───────────────────


def _entry(doc: Doc, esc) -> str:
    return (
        f'                    <li><a href="{doc.path.lstrip("/")}">{esc(doc.plain_title)}</a>'
        f'<span class="doc-list__about">{esc(doc.description)}</span></li>'
    )


def index_text(all_docs: list[Doc]) -> str:
    """The section list on the Docs page: each section's index as its
    heading and lede, then its other docs."""
    blocks = "\n".join(_section_block(key, all_docs) for key in SECTIONS)
    return sitemd.with_block(INDEX.read_text(encoding="utf-8"), blocks, BEGIN, END, "app/docs.html")


def _section_block(key: str, all_docs: list[Doc]) -> str:
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    index = next(d for d in all_docs if d.section == key and d.is_index)
    others = [d for d in all_docs if d.section == key and not d.is_index]
    lines = [
        f'            <div class="doc-section" id="{key}">',
        f'                <h3><a href="{index.path.lstrip("/")}">{esc(section_name(key))}</a></h3>',
        f'                <p class="doc-section__lede">{esc(index.description)}</p>',
    ]
    if others:
        items = "\n".join(_entry(d, esc) for d in others)
        lines.append(f'                <ul class="doc-list">\n{items}\n                </ul>')
    lines.append("            </div>")
    return "\n".join(lines)


def sitemap_text(all_docs: list[Doc]) -> str:
    entries = "\n".join(
        "  <url>\n"
        f"    <loc>{SITE_URL}{doc.path.lstrip('/')}</loc>\n"
        "    <changefreq>monthly</changefreq>\n"
        "    <priority>0.5</priority>\n"
        "  </url>"
        for doc in all_docs
    )
    return sitemd.with_block(SITEMAP.read_text(encoding="utf-8"), "  " + entries.strip(), BEGIN, END, "app/sitemap.xml")


def llms_text(all_docs: list[Doc]) -> str:
    entries = "\n".join(
        f"- [{section_name(doc.section)}: {doc.plain_title}]({SITE_URL}{doc.path.lstrip('/')}): {doc.description}"
        for doc in all_docs
    )
    return sitemd.with_block(LLMS.read_text(encoding="utf-8"), entries, BEGIN, END, "app/llms.txt")


# ── main ─────────────────────────────────────────────────────────


def sync_pages(found: list[Doc], check: bool) -> int:
    """Write or check every doc page and report strays; problems found."""
    problems = 0
    wanted = set()
    for doc in found:
        target = SITE / doc.path.lstrip("/")
        wanted.add(target)
        rel = target.relative_to(ROOT)
        try:
            page = render(doc, found)
        except RenderError as exc:
            print(f"✗ {exc}")
            problems += 1
            continue
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
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
    for stray in sorted(p for p in OUT.rglob("*") if p.is_file()) if OUT.exists() else []:
        if stray not in wanted:
            print(f"✗ {stray.relative_to(ROOT)} has no doc; delete it")
            problems += 1
    return problems


def sync_blocks(found: list[Doc], check: bool) -> int:
    """Write or check the doc blocks in the Docs page, the sitemap and llms.txt; problems found."""
    problems = 0
    for path, build in ((INDEX, index_text), (SITEMAP, sitemap_text), (LLMS, llms_text)):
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
            print(f"✗ {rel}'s doc entries are stale; run `{TASK}`")
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
        found = docs()
    except RenderError as exc:
        print(f"✗ {exc}")
        return 1
    if not found:
        print("docsite: no docs under docs/", file=sys.stderr)
        return 2
    DIAGRAMS.clear()
    problems = sync_pages(found, args.check)
    register_lesson_diagrams()
    problems += sync_diagrams(args.check) + sync_blocks(found, args.check)
    if problems:
        print(f"docsite: {problems} problem(s)")
        return 1
    print(f"docsite: {len(found)} page(s) {'current' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
