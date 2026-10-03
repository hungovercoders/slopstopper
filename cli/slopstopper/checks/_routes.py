"""Shared helpers for the AGENTS.md-first docs checks.

`hygiene:entry-files` and `hygiene:docs-structure` both read the same
things out of a markdown file: how many tokens it costs an agent to load,
which docs it links, and whether each link is a *route* an agent will
actually follow. One copy, so the two checks agree on what a route is.

A route is a logical line (paragraph, bullet or table row — fenced code
is skipped) that links a `.md` file AND names a trigger AND says read:

    Before you change CI, read docs/ci.md — it defines what `task ci` runs.
    | adding a check | Read [hygiene/README.md](hygiene/README.md) first |

"See docs/ci.md for details" is a soft link: agents treat it as optional
and skip it, then reinvent what the doc already settled. A line with the
trigger stated and the verb "read" gets followed. That measured
difference is the whole reason the checks insist on the form.
"""

from __future__ import annotations

import re
from pathlib import Path

# Tokens are estimated as chars/4 — coarse, but stable, dependency-free
# and far closer to what a tokenizer charges for link-heavy markdown
# than a word count is (a 1,400-word AGENTS.md full of tables and links
# costs ~3,200 tokens, not ~2,000).
_BADGE_LINE_RE = re.compile(r"^\s*(?:\[?!\[[^\]]*\]\([^)]*\)\]?(?:\([^)]*\))?\s*)+$")
_DOC_LINK_RE = re.compile(r"\]\(\s*<?([^)\s>#]+\.md)(?:#[^)\s>]*)?>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
_BLOCK_START_RE = re.compile(r"^\s*(#|\||[-*+]\s|\d+[.)]\s|>)")
_READ_CUE_RE = re.compile(r"\b(read|open|load|follow)\b", re.I)
# "For <situation>, read X" is trigger-first too; "read X for details" is not.
_TRIGGER_CUE_RE = re.compile(
    r"\b(before|when|if|whenever|unless|first|any task)\b|^\W*for\b", re.I
)
_ROUTE_TEMPLATE = "Before you <do X>, read <doc> — <what it holds>"


def estimate_tokens(text: str) -> int:
    """Estimated token cost of `text`, badge-only lines excluded.

    A README's pipeline-status badges are images a reader never parses
    as prose; counting their URLs would charge the budget for a block
    `slopstopper badges` generates. Everything else counts.
    """
    kept = [line for line in text.splitlines() if not _BADGE_LINE_RE.match(line)]
    return len("\n".join(kept)) // 4


def count_lines(text: str) -> int:
    return len(text.splitlines())


_TABLE_ROW_RE = re.compile(r"^\s*\|")
_TABLE_RULE_RE = re.compile(r"^\s*\|?\s*:?-{2,}")


def _first_cell(row: str) -> str:
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return cells[0] if cells else ""


class _Joiner:
    """Accumulates source lines into logical lines (see `logical_lines`)."""

    def __init__(self) -> None:
        self.out: list[str] = []
        self.current: str | None = None
        self.table_prefix = ""

    def flush(self) -> None:
        if self.current is not None:
            self.out.append(self.current)
        self.current = None

    def blank(self) -> None:
        self.flush()
        self.table_prefix = ""

    def table_row(self, stripped: str) -> None:
        self.flush()
        if _TABLE_RULE_RE.match(stripped.lstrip("|").strip()):
            return
        first = _first_cell(stripped)
        if not self.table_prefix and _TRIGGER_CUE_RE.search(first) and not doc_links(stripped):
            self.table_prefix = first + " "  # the header row: its first cell is the trigger
            return
        self.current = self.table_prefix + stripped

    def block_start(self, stripped: str) -> None:
        self.flush()
        self.current = stripped
        self.table_prefix = ""

    def continuation(self, stripped: str) -> None:
        self.current += " " + stripped  # type: ignore[operator]


def logical_lines(text: str) -> list[str]:
    """Paragraphs, bullets and table rows as single strings.

    Wrapped prose is joined so a route split over two source lines still
    reads as one; fenced code blocks are skipped (a link inside a code
    sample is an example, not a route). A row of a routing table — one
    whose header's first cell is the trigger ("When you are…") — comes
    back with that header prefixed, so the row reads as the trigger-first
    sentence it is: the column header *is* the trigger.
    """
    joiner = _Joiner()
    fenced = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
        elif fenced:
            continue
        elif not stripped:
            joiner.blank()
        elif _TABLE_ROW_RE.match(line):
            joiner.table_row(stripped)
        elif joiner.current is None or _BLOCK_START_RE.match(line):
            joiner.block_start(stripped)
        else:
            joiner.continuation(stripped)
    joiner.flush()
    return joiner.out


def doc_links(line: str) -> list[str]:
    """Relative `.md` link targets on one logical line (URLs excluded)."""
    return [
        t for t in _DOC_LINK_RE.findall(line)
        if not t.startswith(("http://", "https://", "mailto:", "/"))
    ]


def is_explicit_route(line: str) -> bool:
    return bool(_READ_CUE_RE.search(line) and _TRIGGER_CUE_RE.search(line))


def resolve(source: Path, target: str) -> Path | None:
    try:
        return (source.parent / target).resolve()
    except (OSError, ValueError):
        return None


def route_table(source: Path) -> tuple[dict[Path, str], dict[Path, str]]:
    """Split the `.md` links in `source` into explicit routes and soft links.

    Returns `(explicit, soft)`, each mapping the resolved target to the
    first logical line that mentions it. A doc that is routed explicitly
    on one line and mentioned softly on another counts as routed; a doc
    with only soft mentions is unreachable in practice.
    """
    explicit: dict[Path, str] = {}
    soft: dict[Path, str] = {}
    try:
        text = source.read_text()
    except OSError:
        return explicit, soft
    for line in logical_lines(text):
        targets = doc_links(line)
        if not targets:
            continue
        bucket = explicit if is_explicit_route(line) else soft
        for target in targets:
            resolved = resolve(source, target)
            if resolved is not None:
                bucket.setdefault(resolved, line)
    for doc in explicit:
        soft.pop(doc, None)
    return explicit, soft


def soft_route_message(source: str, target: str, line: str) -> str:
    return (
        f"{source}: soft route to {target}: \"{line[:70]}\". A route agents follow "
        f"names its trigger and says read: '{_ROUTE_TEMPLATE}'."
    )


def route_snippet(target: str, holds: str) -> str:
    """A paste-ready explicit route to `target`."""
    return f"Before you <do X>, read [`{target}`](./{target}) — {holds}."
