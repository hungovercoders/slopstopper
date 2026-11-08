#!/usr/bin/env python3
"""Render the reference docs as pages of the site.

The docs under docs/ are markdown, routed from AGENTS.md and read on
GitHub; a visitor to slopstopper.dev who followed a "learn more" link
used to land on GitHub too. The site has no build step, so the pages are
written here and committed, the way the lesson pages are. Each
`docs/<dir>/<NAME>.md` becomes `app/docs/<dir>/<name>.html` (a README its
directory's `index.html`), in the site's own chrome read from
`app/docs.html`, with a breadcrumb, the other docs of its section, and
a line saying which file it is rendered from. The lessons under
docs/learn/ are the course's pages under /learn/ (`scripts/learnsite.py`)
and are not rendered twice; the syllabus, the episode conventions and
the lesson template are.

A `mermaid` fence becomes a diagram: the page shows an SVG per theme
from `app/assets/docs/diagrams/<digest>-{light,dark}.svg`, with the
Mermaid source folded beneath it for readers and screen readers, where
`<digest>` is the first twelve hex digits of the source's SHA-256. This
script writes the source beside them as `<digest>.mmd` and reports a
diagram whose SVGs are missing; `scripts/diagrams.js` renders them
(`task contributing:docs:diagrams`), because the site's CSP allows no
script or inline style, so a diagram cannot render in the browser.

`scripts/sitemd.py` holds the converter and the page template, shared
with the course. A construct outside the markdown it covers fails the
render with the file and line. A relative link to another doc becomes
that doc's page, to a lesson that lesson's page, to any other file in
the repo its view on GitHub; a link to a file that is not there fails
the render, so the pages never carry a dead link.

Each section has an audience. The docs an adopter reads (the checks,
the runbooks, the architecture they meet) and the docs about running
this repository and its site (contributing, decisions, the site, the
course's authoring notes) are listed apart on the Docs page, between
`<!-- docs:adopters:begin -->` … `end` and `<!-- docs:project:begin -->`
… `end`, and a page's kicker says which it is. `app/sitemap.xml` and
`app/llms.txt` carry one entry per page between `<!-- docs:begin -->`
and `<!-- docs:end -->`. This script owns those blocks and nothing else
in the three files. `reliability:sitemap` hard-fails
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
import hashlib
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from posixpath import dirname, normpath, relpath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sitemd  # noqa: E402
from sitemd import BLOB, ROOT, SITE, SITE_URL, Options, Page, RenderError, plain  # noqa: E402

DOCS = ROOT / "docs"
OUT = SITE / "docs"
INDEX = SITE / "docs.html"
SITEMAP = SITE / "sitemap.xml"
LLMS = SITE / "llms.txt"
BEGIN, END = "<!-- docs:begin -->", "<!-- docs:end -->"
GENERATOR, TASK = "scripts/docsite.py", "task contributing:docs:site"
DIAGRAMS_PATH = "/assets/docs/diagrams"
DIAGRAMS_DIR = SITE / DIAGRAMS_PATH.lstrip("/")
DIAGRAMS_TASK = "task contributing:docs:diagrams"
THEMES = ("light", "dark")
_VIEWBOX = re.compile(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"')

# Every Mermaid diagram the pages rendered in this run, digest → source;
# sync_diagrams() keeps app/assets/docs/diagrams/ in step with it.
DIAGRAMS: dict[str, str] = {}

# Every directory under docs/ that holds docs, in the order the Docs page
# lists them, with the name the kicker and breadcrumb use and who the
# section is for: "adopters" (someone running the suite in their repo) or
# "project" (someone working on this repository or its site). A directory
# missing here fails the render rather than being left off the page.
ADOPTERS, PROJECT = "adopters", "project"
SECTIONS = {
    "runbooks": ("Runbooks", ADOPTERS),
    "hygiene": ("Hygiene", ADOPTERS),
    "security": ("Security", ADOPTERS),
    "reliability": ("Reliability", ADOPTERS),
    "architecture": ("Architecture", ADOPTERS),
    "support": ("Support", ADOPTERS),
    "contributing": ("Contributing", PROJECT),
    "deployment": ("Deployment", PROJECT),
    "app": ("The site", PROJECT),
    "decisions": ("Decisions", PROJECT),
    "learn": ("The course", PROJECT),
}
AUDIENCE_KICKER = {ADOPTERS: "Docs", PROJECT: "Inside the project"}
CURRENT = ' aria-current="page"'

# A doc whose audience is not its section's: the release runbook is how
# the project ships slopstopper-cli, not something an adopter does.
AUDIENCE_OVERRIDES = {
    "docs/runbooks/RELEASE.md": PROJECT,
}


def section_name(key: str) -> str:
    return SECTIONS[key][0]


def audience(doc: "Doc") -> str:
    """Who a doc is for: its own override, else its section's audience;
    the map itself is the project's."""
    if doc.where in AUDIENCE_OVERRIDES:
        return AUDIENCE_OVERRIDES[doc.where]
    return SECTIONS[doc.section][1] if doc.section else PROJECT

_H1 = re.compile(r"^# (.+?)\s*$")
_LESSON = re.compile(r"\d\d-[\w-]+\.md")


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
    def section(self) -> str | None:
        """The directory under docs/, or None for the map itself."""
        parts = self.where.split("/")
        return parts[1] if len(parts) == 3 else None

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
    """Every doc the site renders, the map first, then by section order and name."""
    found = []
    for path in sorted(DOCS.rglob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        if sitemd.doc_page(rel) is None:
            raise RenderError(f"{rel}: deeper than docs/<dir>/, which the site does not render")
        if path.parent.name == "learn" and _LESSON.fullmatch(path.name):
            continue
        text = path.read_text(encoding="utf-8")
        m = _H1.match(text.split("\n", 1)[0])
        if not m:
            raise RenderError(f"{rel}:1: expected '# Title' on the first line")
        found.append(Doc(path, m.group(1), text))
    for doc in found:
        if doc.section is not None and doc.section not in SECTIONS:
            raise RenderError(f"{doc.where}: docs/{doc.section}/ is not in docsite.SECTIONS; add it with a name")
    order = list(SECTIONS)
    return sorted(found, key=lambda d: (d.section is not None, order.index(d.section) if d.section else -1,
                                        not d.is_index, d.source.name.lower()))


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


def digest_of(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]


def svg_size(path: Path) -> str:
    """` width="W" height="H"` from a rendered SVG's viewBox, so the page
    reserves the diagram's space before the image arrives; empty when the
    SVG is not there yet."""
    if not path.is_file():
        return ""
    m = _VIEWBOX.search(path.read_text(encoding="utf-8"))
    return f' width="{round(float(m.group(1)))}" height="{round(float(m.group(2)))}"' if m else ""


def diagram_html(source: str, page_dir: str) -> str:
    """A Mermaid fence as the page shows it: one image per theme and the
    source folded beneath, which is also what a screen reader gets."""
    digest = digest_of(source)
    DIAGRAMS[digest] = source
    images = "\n".join(
        f'  <img class="only-{theme}" src="{relpath(f"{DIAGRAMS_PATH}/{digest}-{theme}.svg", page_dir)}"'
        f'{svg_size(DIAGRAMS_DIR / f"{digest}-{theme}.svg")} alt="Diagram; its text follows.">'
        for theme in THEMES
    )
    return (
        '<figure class="diagram">\n'
        f"{images}\n"
        '  <details class="details diagram__source">\n'
        "    <summary>The diagram as text</summary>\n"
        f'    <div class="details__body">{sitemd.fence("", source)}</div>\n'
        "  </details>\n"
        "</figure>"
    )


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
    if doc.section is None:
        items.append(f'<li aria-current="page">{esc(doc.plain_title)}</li>')
    elif doc.is_index:
        items.append(f'<li aria-current="page">{esc(section_name(doc.section))}</li>')
    else:
        items.append(f'<li><a href="index.html">{esc(section_name(doc.section))}</a></li>')
        items.append(f'<li aria-current="page">{esc(doc.plain_title)}</li>')
    return '<nav class="doc-crumbs" aria-label="Breadcrumb"><ol>' + "".join(items) + "</ol></nav>"


def _siblings(doc: Doc, all_docs: list[Doc], esc) -> str:
    """The other pages of the doc's section; for the map, every section's index."""
    rel = lambda p: relpath(p, dirname(doc.path))  # noqa: E731
    if doc.section is None:
        heading, pages = "The sections", [d for d in all_docs if d.is_index and d.section]
        label = lambda d: section_name(d.section)  # noqa: E731
    else:
        heading, pages = f"In {section_name(doc.section)}", [d for d in all_docs if d.section == doc.section]
        label = lambda d: d.plain_title  # noqa: E731
    items = "\n".join(
        f'    <li><a href="{rel(d.path)}"{CURRENT if d is doc else ""}>{esc(label(d))}</a></li>'
        for d in pages
    )
    return f'<nav class="doc-siblings" aria-label="{esc(heading)}">\n  <h2>{esc(heading)}</h2>\n  <ul>\n{items}\n  </ul>\n</nav>'


def render(doc: Doc, all_docs: list[Doc]) -> str:
    opts = options(doc)
    where = doc.where
    content = sitemd.dedupe_ids(sitemd.convert(doc.body, where, opts, base=2))
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    section = section_name(doc.section) if doc.section else "The map"
    main = f"""        <section class="hero hero--lesson hero--doc">
            <span class="kicker">📚 {AUDIENCE_KICKER[audience(doc)]} · {esc(section)}</span>
            <h1>{sitemd.inline(doc.title, where, opts)}</h1>
        </section>
        {_crumbs(doc, esc)}
        <article class="lesson doc">
{content}
        </article>
{_siblings(doc, all_docs, esc)}
        <p class="lesson-source"><a href="{BLOB}{where}" rel="noopener noreferrer">Edit this page on GitHub</a></p>"""
    page = Page(
        source=where, generator=GENERATOR, task=TASK,
        title=doc.plain_title if doc.section is None else f"{doc.plain_title} · {section}",
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
    """The section lists on the Docs page, one per audience: each section's
    index as its heading and lede, then its other docs."""
    text = INDEX.read_text(encoding="utf-8")
    for who in (ADOPTERS, PROJECT):
        begin, end = f"<!-- docs:{who}:begin -->", f"<!-- docs:{who}:end -->"
        text = sitemd.with_block(text, _section_blocks(all_docs, who), begin, end, "app/docs.html")
    return text


def _section_blocks(all_docs: list[Doc], who: str) -> str:
    """One block per section that has a doc for this audience: the index's
    heading and lede when the index is theirs, then the docs that are."""
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    blocks = []
    for key, (name, _) in SECTIONS.items():
        index = next((d for d in all_docs if d.section == key and d.is_index), None)
        if index is None:
            raise RenderError(f"docs/{key}/README.md is missing; every section in docsite.SECTIONS needs its index")
        others = [d for d in all_docs if d.section == key and not d.is_index and audience(d) == who]
        if audience(index) != who and not others:
            continue
        items = "\n".join(_entry(d, esc) for d in others)
        lede = f'                <p class="doc-section__lede">{esc(index.description)}</p>\n' if audience(index) == who else ""
        blocks.append(
            f'            <div class="doc-section" id="{key}{"" if audience(index) == who else "-" + who}">\n'
            f'                <h3><a href="{index.path.lstrip("/")}">{esc(name)}</a></h3>\n'
            + lede
            + (f'                <ul class="doc-list">\n{items}\n                </ul>\n' if items else "")
            + "            </div>"
        )
    return "\n".join(blocks)


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
    def label(doc: Doc) -> str:
        return doc.plain_title if doc.section is None else f"{section_name(doc.section)}: {doc.plain_title}"

    def group(who: str) -> str:
        return "\n".join(
            f"- [{label(doc)}]({SITE_URL}{doc.path.lstrip('/')}): {doc.description}"
            for doc in all_docs if audience(doc) == who
        )

    entries = f"For adopters:\n\n{group(ADOPTERS)}\n\nInside the project:\n\n{group(PROJECT)}"
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
    problems = sync_pages(found, args.check) + sync_diagrams(args.check) + sync_blocks(found, args.check)
    if problems:
        print(f"docsite: {problems} problem(s)")
        return 1
    print(f"docsite: {len(found)} page(s) {'current' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
