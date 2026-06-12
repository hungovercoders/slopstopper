"""Documentation structure validator.

Ports .ss/scripts/check-docs-structure.py + generate-docs-structure-md.py.
Validates that the docs/ tree matches the governance model declared
in docs/index.md (each category named in the index must exist with a
README.md; nothing in docs/ should exist that the index doesn't sanction).

Writes a JSON report (machine-readable, drives downstream tooling) and a
markdown report (human-readable). Exit codes mirror the bash:

  0 — clean
  1 — violations OR docs/ / docs/index.md missing
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

DOCS_DIR = Path("docs")
INDEX_PATH = DOCS_DIR / "index.md"
REPORT_DIR = Path(".ss/reports/docs")
REPORT_JSON = REPORT_DIR / "docs-structure-report.json"
REPORT_MD = REPORT_DIR / "docs-structure-report.md"

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
        print("❌ docs/ directory not found")
        return None
    index_path = docs_dir / "index.md"
    if not index_path.exists():
        print("❌ docs/index.md not found")
        return None
    expected = _extract_categories(index_path.read_text())
    violations = _check_expected_categories(docs_dir, expected)
    violations += _check_unexpected_items(docs_dir, expected)
    return violations, expected


def run(_args: list[str] | None = None) -> int:
    print("🔍 Validating documentation structure...")

    result = _check_structure(DOCS_DIR)
    if result is None:
        return 1
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
        print(f"❌ Found {len(violations)} structure violation(s)")
        return 1
    print("✅ Documentation structure is valid")
    return 0
