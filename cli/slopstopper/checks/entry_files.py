"""Entry-file size budget + Map Pattern pointer check.

Ports .ss/scripts/check-entry-file-size.py. Enforces two coupled rules
declared in docs/index.md ("The Map Pattern"):

  1. Agent entry files (README.md, AGENTS.md, CLAUDE.md) stay under a
     word budget so they don't crowd the context window of every agent
     conversation.
  2. README.md and AGENTS.md must each link to docs/index.md (the map),
     CLAUDE.md must be a thin pointer to AGENTS.md (a link or the
     `@AGENTS.md` import directive), and docs/index.md itself must exist.
     A budget without the pointer is pointless: the map only works if
     the entry files actually defer to it.

Writes a markdown report and a JSON report under .ss/reports/entry-files/.
The markdown report includes a paste-ready snippet for each missing
pointer so adopters can remediate in one copy/paste.

Configuration (.slopstopper.yml — optional):

    hygiene:
      entry_files:
        max_words: 1500              # ≈ 2k tokens for English prose
        require_map_pointer: true    # enforce the Map Pattern pointer rule
        map_path: docs/index.md      # path to the docs map (relative to repo root)

See .slopstopper.yml.example for the canonical schema.

Exit codes:
  0 — all entry files within budget AND pointer rule satisfied
  1 — at least one budget OR pointer violation
  2 — required input files missing
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from slopstopper import config, output

ENTRY_FILES = ("README.md", "AGENTS.md", "CLAUDE.md")
MAP_POINTER_FILES = ("README.md", "AGENTS.md")
CLAUDE_FILE = "CLAUDE.md"
AGENTS_FILE = "AGENTS.md"
DEFAULT_MAX_WORDS = 1500
DEFAULT_MAP_PATH = "docs/index.md"
REPORT_DIR = Path(".ss/reports/entry-files")
REPORT_MD = REPORT_DIR / "entry-file-size-report.md"
REPORT_JSON = REPORT_DIR / "entry-file-size-report.json"

# Consumed by `slopstopper emit hygiene:entry-files --target pr-comment`.
# The discriminator is byte-identical to the marker the legacy
# actions/github-script@v7 block matched on, so the same bot comment
# is reused after the workflow flip. No issue keys: the workflow gates
# main with the check's own exit code, no main-branch issue is created.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "📏 Entry-File Budget Check",
}

_WORD_RE = re.compile(r"\S+")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_AGENTS_DIRECTIVE_RE = re.compile(r"^@AGENTS\.md\s*$", re.MULTILINE)


def _config_int(path: str, default: int) -> int:
    raw = config.get(path, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _config_bool(path: str, default: bool) -> bool:
    raw = config.get(path, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "yes", "1", "on")
    return default


def _config_str(path: str, default: str) -> str:
    raw = config.get(path, default)
    if raw is None:
        return default
    return str(raw)


def _load_max_words() -> int:
    return _config_int("hygiene.entry_files.max_words", DEFAULT_MAX_WORDS)


def _load_require_map_pointer() -> bool:
    return _config_bool("hygiene.entry_files.require_map_pointer", True)


def _load_map_path() -> str:
    return _config_str("hygiene.entry_files.map_path", DEFAULT_MAP_PATH)


def _count_words(path: Path) -> int:
    return len(_WORD_RE.findall(path.read_text()))


def _link_targets(text: str) -> list[str]:
    return [m.group(2) for m in _MD_LINK_RE.finditer(text)]


def _link_resolves_to(target: str, source: Path, expected: Path) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    # Strip fragment + query so docs/index.md#anchor still counts.
    bare = target.split("?")[0].split("#")[0]
    if not bare:
        return False
    try:
        resolved = (source.parent / bare).resolve()
    except (OSError, ValueError):
        return False
    return resolved == expected


def _has_map_pointer(file_path: Path, map_file: Path) -> bool:
    try:
        text = file_path.read_text()
    except OSError:
        return False
    expected = map_file.resolve()
    for target in _link_targets(text):
        if _link_resolves_to(target, file_path, expected):
            return True
    return False


def _has_agents_pointer(file_path: Path) -> bool:
    try:
        text = file_path.read_text()
    except OSError:
        return False
    if _AGENTS_DIRECTIVE_RE.search(text):
        return True
    expected = Path(AGENTS_FILE).resolve()
    for target in _link_targets(text):
        if _link_resolves_to(target, file_path, expected):
            return True
    return False


def _check_pointer(name: str, map_file: Path) -> str | None:
    """Return a violation key for this entry file, or None if compliant."""
    path = Path(name)
    if name == CLAUDE_FILE:
        return None if _has_agents_pointer(path) else "claude_not_thin_pointer"
    if name in MAP_POINTER_FILES:
        return None if _has_map_pointer(path, map_file) else "missing_map_pointer"
    return None


def _measure(name: str, max_words: int, map_file: Path, require_pointer: bool) -> dict | None:
    path = Path(name)
    if not path.exists():
        return None
    words = _count_words(path)
    pointer_violation = _check_pointer(name, map_file) if require_pointer else None
    return {
        "file": name,
        "words": words,
        "budget": max_words,
        "over_budget": words > max_words,
        "headroom": max_words - words,
        "pointer_ok": pointer_violation is None,
        "pointer_violation": pointer_violation,
    }


def _measure_all(
    max_words: int, map_file: Path, require_pointer: bool
) -> tuple[list[dict], list[str]]:
    measurements: list[dict] = []
    missing: list[str] = []
    for name in ENTRY_FILES:
        m = _measure(name, max_words, map_file, require_pointer)
        if m is None:
            missing.append(name)
        else:
            measurements.append(m)
    return measurements, missing


def _generated_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _has_violations(measurements: list[dict], map_file_missing: bool) -> bool:
    if map_file_missing:
        return True
    return any(m["over_budget"] or not m["pointer_ok"] for m in measurements)


def _status_line(clean: bool, max_words: int) -> str:
    if clean:
        return "✅ All entry files within budget and pointing at the map."
    return (
        f"❌ One or more entry files exceed the {max_words:,}-word budget "
        "or are missing the Map Pattern pointer."
    )


def _md_row(m: dict) -> str:
    size_status = "❌ over" if m["over_budget"] else "✅ ok"
    pointer_status = "✅ ok" if m["pointer_ok"] else "❌ missing"
    return (
        f"| `{m['file']}` | {m['words']} | {m['budget']} | "
        f"{size_status} | {m['headroom']:+d} | {pointer_status} |"
    )


def _map_pointer_snippet(map_path: str) -> str:
    return (
        f"> 🗺️ **Documentation map.** [`{map_path}`](./{map_path}) is the "
        "single index of all project documentation. This file is "
        "intentionally thin — it points at the map rather than duplicating "
        "its content."
    )


def _claude_pointer_snippet() -> str:
    return (
        "# Claude Code — project instructions\n\n"
        "The canonical agent conventions for this repo live in "
        "[`AGENTS.md`](./AGENTS.md). Claude Code imports them via the "
        "directive below — keep this file thin and let `AGENTS.md` be "
        "the single source of truth.\n\n"
        "@AGENTS.md"
    )


def _map_file_snippet(map_path: str) -> str:
    return (
        f"# Documentation Index\n\n"
        f"This file is **the map** — every other entry point in the repo "
        f"defers to it.\n\n"
        f"| Category | Purpose | README |\n"
        f"| -------- | ------- | ------ |\n"
        f"| [example/](example/) | Replace with a real category | "
        f"[README](example/README.md) |\n"
    )


def _build_fix_section(
    measurements: list[dict],
    map_path: str,
    map_file_missing: bool,
) -> str:
    sections: list[str] = []
    for m in measurements:
        if m["over_budget"]:
            sections.append(
                f"### `{m['file']}` is over the word budget\n\n"
                f"Move bulk into the category README under `docs/` that owns the "
                f"topic, leaving a one-line pointer in the entry file. See "
                f"[the Map Pattern](./{map_path}#the-map-pattern).\n"
            )
        if m["pointer_violation"] == "missing_map_pointer":
            sections.append(
                f"### `{m['file']}` is missing the Map Pattern pointer\n\n"
                f"Paste this near the top of `{m['file']}`:\n\n"
                f"```markdown\n{_map_pointer_snippet(map_path)}\n```\n"
            )
        if m["pointer_violation"] == "claude_not_thin_pointer":
            sections.append(
                f"### `CLAUDE.md` is not a thin pointer to `AGENTS.md`\n\n"
                f"Replace the contents of `CLAUDE.md` with:\n\n"
                f"```markdown\n{_claude_pointer_snippet()}\n```\n\n"
                f"Claude Code reads the `@AGENTS.md` directive automatically — "
                f"keep this file short and let `AGENTS.md` carry the project "
                f"conventions.\n"
            )
    if map_file_missing:
        sections.append(
            f"### `{map_path}` does not exist\n\n"
            f"The Map Pattern requires a docs index at `{map_path}`. Create "
            f"it with at minimum:\n\n"
            f"```markdown\n{_map_file_snippet(map_path)}```\n\n"
            f"Then add one `docs/<category>/README.md` per row of the table. "
            f"`task ss:hygiene:docs-structure` validates the tree against this "
            f"map.\n"
        )
    if not sections:
        return ""
    return "## How to fix violations\n\n" + "\n".join(sections)


def _build_md_report(
    measurements: list[dict],
    generated_at: str,
    status_line: str,
    map_path: str,
    map_file_missing: bool,
) -> str:
    rows = "\n".join(_md_row(m) for m in measurements)
    map_block = (
        f"## Map file\n\n"
        f"❌ `{map_path}` not found. The Map Pattern requires a docs index.\n"
        if map_file_missing
        else ""
    )
    fix_section = _build_fix_section(measurements, map_path, map_file_missing)
    fix_block = f"\n{fix_section}\n" if fix_section else ""
    return f"""# 📏 Entry-File Size + Map Pattern Report

**Generated:** {generated_at}

The repo's agent entry files (`README.md`, `AGENTS.md`, `CLAUDE.md`)
are loaded into every agent conversation. `docs/index.md` declares
that they should stay under ~2k tokens each AND link to the docs map
so agents converge on a single source of truth. This check enforces
both: a 1,500-word cap (≈ 2k tokens for English prose) and the Map
Pattern pointer rule.

## Measurements

| File | Words | Budget | Size | Headroom | Pointer |
| ---- | ----- | ------ | ---- | -------- | ------- |
{rows}

{map_block}## Status

{status_line}
{fix_block}
---

*Generated by `task ss:hygiene:entry-files`.*
"""


def _build_json_report(
    measurements: list[dict],
    generated_at: str,
    max_words: int,
    map_path: str,
    map_file_missing: bool,
    require_pointer: bool,
    clean: bool,
) -> str:
    payload = {
        "generated_at": generated_at,
        "budget_words": max_words,
        "map_path": map_path,
        "map_file_present": not map_file_missing,
        "require_map_pointer": require_pointer,
        "measurements": measurements,
        "clean": clean,
        "violation_count": (
            sum(1 for m in measurements if m["over_budget"] or not m["pointer_ok"])
            + (1 if map_file_missing else 0)
        ),
    }
    return json.dumps(payload, indent=2)


def _print_summary(
    measurements: list[dict],
    status_line: str,
    map_path: str,
    map_file_missing: bool,
) -> None:
    output.status("📏", "Entry-file size + Map Pattern check")
    output.separator()
    for m in measurements:
        size_marker = "❌" if m["over_budget"] else "✅"
        pointer_marker = "❌" if not m["pointer_ok"] else "✅"
        output._emit(
            f"  {size_marker} {m['file']:<14} {m['words']:>5} words  "
            f"(budget {m['budget']}, headroom {m['headroom']:+d})  "
            f"{pointer_marker} pointer"
        )
    if map_file_missing:
        output._emit(f"  ❌ {map_path} not found")
    output.blank()
    output._emit(status_line)
    output.footer(REPORT_DIR, [REPORT_MD.name])


def run(_args: list[str] | None = None) -> int:
    max_words = _load_max_words()
    require_pointer = _load_require_map_pointer()
    map_path = _load_map_path()
    map_file = Path(map_path)
    map_file_missing = require_pointer and not map_file.exists()

    measurements, missing = _measure_all(max_words, map_file, require_pointer)

    if missing:
        output.error(f"Required entry files not found: {', '.join(missing)}")
        return 2

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    clean = not _has_violations(measurements, map_file_missing)
    generated_at = _generated_at()
    status_line = _status_line(clean, max_words)

    REPORT_JSON.write_text(
        _build_json_report(
            measurements, generated_at, max_words, map_path,
            map_file_missing, require_pointer, clean,
        )
    )
    REPORT_MD.write_text(
        _build_md_report(measurements, generated_at, status_line, map_path, map_file_missing)
    )

    _print_summary(measurements, status_line, map_path, map_file_missing)
    return 0 if clean else 1
