"""Documentation structure validator.

Ports .ss/scripts/check-docs-structure.py + generate-docs-structure-md.py.
Validates that the docs/ tree matches the governance model declared
in docs/index.md (each category named in the index must exist with a
README.md; nothing in docs/ should exist that the index doesn't sanction;
every doc inside a category is linked from that category's README, so
the index → category README → doc chain is unbroken).

Configuration (.slopstopper.yml — optional):

    hygiene:
      docs_structure:
        require_indexed_docs: true   # the category README → doc rule

Writes a JSON report (machine-readable, drives downstream tooling) and a
markdown report (human-readable).

Exit codes:
  0 — clean
  1 — violations
  2 — docs/ or docs/index.md missing (no map to check against), or
      arguments were passed (this check takes none)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from slopstopper import config, output
from slopstopper.checks._args import reject_extra_args

DOCS_DIR = Path("docs")
INDEX_PATH = DOCS_DIR / "index.md"
REPORT_DIR = Path(".ss/reports/docs")
REPORT_JSON = REPORT_DIR / "docs-structure-report.json"
REPORT_MD = REPORT_DIR / "docs-structure-report.md"

# Consumed by `slopstopper emit hygiene:docs-structure --target {pr-comment,issue}`.
# Strings are byte-for-byte identical to the discriminator / title / labels
# the legacy actions/github-script@v7 block in
# .github/workflows/ss-hygiene-docs-structure-check.yml used, so the same
# bot comments/issues are matched after the workflow flip.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "📋 Documentation Structure",
    "issue_title": "📋 Documentation Structure Issues",
    "issue_labels": ["documentation-structure", "documentation"],
    "issue_followup": "🔔 Documentation structure issues detected again in commit",
}

# Files allowed at the top level of docs/ without being declared in
# the categories table. Mirrors the bash check exactly.
ALLOWED_TOP_FILES = {"index.md", "README.md", "AGENTS.md", "CONTRIBUTING.md"}

_CATEGORY_RE = re.compile(r"\|\s*\[([a-z_]+)/\]\(([a-z_]+)/\)\s*\|")


def _extract_categories(index_text: str) -> list[str]:
    matches = _CATEGORY_RE.findall(index_text)
    return sorted({m[0] for m in matches})


def _check_expected_categories(docs_dir: Path, expected: list[str]) -> list[dict]:
    violations: list[dict] = []
    for category in expected:
        category_path = docs_dir / category
        if not category_path.exists():
            violations.append({
                "type": "missing_directory",
                "path": f"docs/{category}/",
                "message": f"Missing directory: docs/{category}/",
            })
        elif not (category_path / "README.md").exists():
            violations.append({
                "type": "missing_readme",
                "path": f"docs/{category}/README.md",
                "message": f"Missing README.md: docs/{category}/README.md",
            })
    return violations


def _check_unexpected_items(docs_dir: Path, expected: list[str]) -> list[dict]:
    violations: list[dict] = []
    expected_dirs = set(expected)

    actual_files = {f.name for f in docs_dir.iterdir() if f.is_file()}
    for filename in sorted(actual_files - ALLOWED_TOP_FILES):
        violations.append({
            "type": "unexpected_file",
            "path": f"docs/{filename}",
            "message": f"Unexpected file (not in index): docs/{filename}",
        })

    actual_dirs = sorted(d.name for d in docs_dir.iterdir() if d.is_dir())
    for dirname in sorted(set(actual_dirs) - expected_dirs):
        violations.append({
            "type": "unexpected_directory",
            "path": f"docs/{dirname}/",
            "message": f"Unexpected directory (not in index): docs/{dirname}/",
        })

    return violations


# Inline `](target)` / `](target "title")`, reference definitions
# `[ref]: target`, and HTML `href="target"` — the three ways a README can
# point at a sibling doc.
_LINK_TARGET_RES = (
    re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"),
    re.compile(r"^\s*\[[^\]]+\]:\s*<?([^\s>]+)>?", re.M),
    re.compile(r"""href\s*=\s*["']([^"']+)["']"""),
)


def _linked_files(readme: Path) -> set[Path]:
    """Files a category README links to, resolved relative to it.

    Resolved paths, not basenames: a link to a same-named file in another
    category must not count as indexing this category's copy.
    """
    out: set[Path] = set()
    text = readme.read_text()
    for pattern in _LINK_TARGET_RES:
        for target in pattern.findall(text):
            target = target.split("#", 1)[0].split("?", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            out.add((readme.parent / target).resolve())
    return out


def _indexing_readmes(doc: Path, category_dir: Path) -> list[Path]:
    """READMEs that may index `doc`: one per directory from its own up to the category."""
    out: list[Path] = []
    directory = doc.parent
    while True:
        readme = directory / "README.md"
        if readme.is_file() and readme != doc:
            out.append(readme)
        if directory == category_dir or category_dir not in directory.parents:
            break
        directory = directory.parent
    return out


def _check_category_contents(docs_dir: Path, expected: list[str]) -> list[dict]:
    """Every doc inside a category must be reachable from a README above it.

    The map is a chain: docs/index.md lists categories, each category
    README lists its docs. The first link was always enforced; the second
    was not, so a file could sit in docs/<category>/ that no index anywhere
    mentioned — and "docs/index.md is the single index of all project
    documentation" was true one level deep.

    Sub-directories count: docs/<category>/adr/0001.md is indexed by
    docs/<category>/adr/README.md or docs/<category>/README.md. Turn the
    rule off with `hygiene.docs_structure.require_indexed_docs: false`.
    """
    if not config.get_bool("hygiene.docs_structure.require_indexed_docs", True):
        return []
    violations: list[dict] = []
    links: dict[Path, set[Path]] = {}
    for category in expected:
        category_dir = docs_dir / category
        readme = category_dir / "README.md"
        if not readme.is_file():
            continue  # reported by _check_expected_categories
        for doc in sorted(category_dir.rglob("*.md")):
            if doc == readme:
                continue
            indexers = _indexing_readmes(doc, category_dir)
            if any(doc.resolve() in links.setdefault(r, _linked_files(r)) for r in indexers):
                continue
            rel = doc.relative_to(docs_dir).as_posix()
            violations.append({
                "type": "unindexed_doc",
                "path": f"docs/{rel}",
                "message": (
                    f"Unindexed doc: docs/{rel} is not linked from "
                    f"docs/{category}/README.md or a README.md above it"
                ),
            })
    return violations


def _generated_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_expected_categories_section(categories: list[str]) -> str:
    if not categories:
        return (
            "## Expected Categories\n\n"
            "_No categories declared in `docs/index.md`. Add a categories table "
            "(see slopstopper's docs/index.md for the format) to enforce structure._\n\n"
        )
    lines = [
        "## Expected Categories",
        "",
        "The following categories are defined in `docs/index.md`:",
        "",
        "| Category | Required | Status |",
        "|----------|----------|--------|",
    ]
    for category in categories:
        lines.append(f"| {category}/ | ✅ | Must exist with README.md |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_violations_content(violations: list[dict]) -> str:
    content = f"Found **{len(violations)}** violation(s):\n\n"
    by_type: dict[str, list[dict]] = {}
    for v in violations:
        by_type.setdefault(v.get("type", "unknown"), []).append(v)

    sections = [
        ("missing_directory", "### Missing Directories\n\n", None),
        ("missing_readme", "### Missing README.md Files\n\n", None),
        (
            "unexpected_file",
            "### Unexpected Files\n\n",
            "  *Either add to `docs/index.md` or remove the file*\n",
        ),
        (
            "unexpected_directory",
            "### Unexpected Directories\n\n",
            "  *Either add to `docs/index.md` or remove the directory*\n",
        ),
        (
            "unindexed_doc",
            "### Unindexed Docs\n\n",
            "  *Link it from the category README (a Contents list is the convention) or remove it*\n",
        ),
    ]

    for vtype, header, note in sections:
        if vtype not in by_type:
            continue
        content += header
        for v in by_type[vtype]:
            content += f"- {v['message']}\n"
            if note:
                content += note
        content += "\n"

    return content


def _build_md_report(data: dict, generated_at: str) -> str:
    violations = data.get("violations", [])
    is_valid = data.get("valid", True)
    status_line = (
        "✅ Documentation structure matches governance model"
        if is_valid
        else "❌ Documentation structure violations found"
    )

    report = (
        f"# 📋 Documentation Structure Report\n"
        f"\n"
        f"**Generated:** {generated_at}\n"
        f"\n"
        f"## Status\n"
        f"\n"
        f"{status_line}\n"
        f"\n"
        f"## Governance Model\n"
        f"\n"
        f"The documentation structure is governed by [`docs/index.md`](../index.md). "
        f"All documentation must align with the categories and structure defined there.\n"
        f"\n"
        f"**Key Principle:** The index is the **sole source of truth** for documentation structure.\n"
        f"\n"
        f"## Violations\n"
        f"\n"
    )

    if violations:
        report += _format_violations_content(violations)
    else:
        report += "✅ No violations found\n\n"

    report += _format_expected_categories_section(data.get("expected_categories", []))

    report += (
        "## How to Fix\n"
        "\n"
        "1. **For missing directories or README.md files:**\n"
        "   - Create the directory and add a README.md with its purpose\n"
        "   - See existing README.md files for the format\n"
        "\n"
        "2. **For unexpected files:**\n"
        "   - If they should be documented: Add an entry to `docs/index.md`\n"
        "   - If they shouldn't exist: Delete them\n"
        "\n"
        "3. **For unexpected directories:**\n"
        "   - If they should be part of governance: Add to the table in `docs/index.md`\n"
        "   - If they shouldn't exist: Delete them\n"
        "\n"
        "4. **For unindexed docs:**\n"
        "   - Link the file from its category's `README.md` — a `## Contents` list is the convention\n"
        "   - The map is a chain (`docs/index.md` → category README → doc); every doc must be on it\n"
        "\n"
        "## More Information\n"
        "\n"
        "- See [`docs/index.md`](../index.md) for the governance model\n"
        "- Each category README.md should document its purpose and contents\n"
        "\n"
        "---\n"
        "\n"
        "*Report generated by Documentation Structure Check*\n"
    )
    return report


def _check_structure(docs_dir: Path) -> tuple[list[dict], list[str]] | None:
    if not docs_dir.exists():
        output.error("docs/ directory not found")
        return None
    index_path = docs_dir / "index.md"
    if not index_path.exists():
        output.error("docs/index.md not found")
        return None
    expected = _extract_categories(index_path.read_text())
    violations = _check_expected_categories(docs_dir, expected)
    violations += _check_unexpected_items(docs_dir, expected)
    violations += _check_category_contents(docs_dir, expected)
    return violations, expected


def run(args: list[str] | None = None) -> int:
    if args:
        return reject_extra_args("hygiene:docs-structure", args)
    output.running("Validating documentation structure…")

    result = _check_structure(DOCS_DIR)
    if result is None:
        return 2
    violations, expected = result

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "violations": violations,
        "valid": len(violations) == 0,
        "violation_count": len(violations),
        "expected_categories": expected,
    }
    REPORT_JSON.write_text(json.dumps(data, indent=2))
    REPORT_MD.write_text(_build_md_report(data, _generated_at()))

    if violations:
        output.error(f"Found {len(violations)} structure violation(s)")
        output.footer(REPORT_DIR, [REPORT_MD.name])
        return 1
    output.success("Documentation structure is valid")
    output.footer(REPORT_DIR, [REPORT_MD.name])
    return 0
