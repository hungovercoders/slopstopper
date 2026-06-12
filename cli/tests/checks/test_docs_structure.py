"""Tests for the hygiene:docs-structure check."""

from __future__ import annotations

import json
from pathlib import Path

from slopstopper.checks import docs_structure


def _seed_index(docs_dir: Path, categories: list[str]) -> None:
    rows = "\n".join(f"| [{c}/]({c}/) | Description |" for c in categories)
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / "index.md").write_text(
        "# Docs map\n\n"
        "| Category | Description |\n"
        "| -------- | ----------- |\n"
        f"{rows}\n"
    )


def _seed_category(docs_dir: Path, name: str, with_readme: bool = True) -> Path:
    cat = docs_dir / name
    cat.mkdir(parents=True, exist_ok=True)
    if with_readme:
        (cat / "README.md").write_text(f"# {name}\n")
    return cat


def test_extract_categories_simple():
    text = (
        "| [hygiene/](hygiene/) | Quality checks |\n"
        "| [security/](security/) | Security checks |\n"
    )
    assert docs_structure._extract_categories(text) == ["hygiene", "security"]


def test_extract_categories_deduplicates_and_sorts():
    text = (
        "| [security/](security/) | A |\n"
        "| [hygiene/](hygiene/) | B |\n"
        "| [hygiene/](hygiene/) | C |\n"
    )
    assert docs_structure._extract_categories(text) == ["hygiene", "security"]


def test_extract_categories_ignores_non_matching_rows():
    text = "| something | other |\n| [hygiene/](hygiene/) | A |\n"
    assert docs_structure._extract_categories(text) == ["hygiene"]


def test_check_expected_categories_clean(isolated_cwd):
    docs = Path("docs")
    docs.mkdir()
    _seed_category(docs, "hygiene")
    _seed_category(docs, "security")
    assert docs_structure._check_expected_categories(docs, ["hygiene", "security"]) == []


def test_check_expected_categories_missing_directory(isolated_cwd):
    docs = Path("docs")
    docs.mkdir()
    _seed_category(docs, "hygiene")
    violations = docs_structure._check_expected_categories(docs, ["hygiene", "security"])
    assert len(violations) == 1
    assert violations[0]["type"] == "missing_directory"
    assert violations[0]["path"] == "docs/security/"


def test_check_expected_categories_missing_readme(isolated_cwd):
    docs = Path("docs")
    docs.mkdir()
    _seed_category(docs, "hygiene", with_readme=False)
    violations = docs_structure._check_expected_categories(docs, ["hygiene"])
    assert len(violations) == 1
    assert violations[0]["type"] == "missing_readme"


def test_check_unexpected_items_flags_unknown_file(isolated_cwd):
    docs = Path("docs")
    docs.mkdir()
    (docs / "stray.md").write_text("hi")
    violations = docs_structure._check_unexpected_items(docs, [])
    assert any(v["type"] == "unexpected_file" and v["path"] == "docs/stray.md" for v in violations)


def test_check_unexpected_items_ignores_allowed_top_files(isolated_cwd):
    docs = Path("docs")
    docs.mkdir()
    for allowed in docs_structure.ALLOWED_TOP_FILES:
        (docs / allowed).write_text(allowed)
    violations = docs_structure._check_unexpected_items(docs, [])
    assert violations == []


def test_check_unexpected_items_flags_undocumented_dir(isolated_cwd):
    docs = Path("docs")
    docs.mkdir()
    _seed_category(docs, "rogue")
    violations = docs_structure._check_unexpected_items(docs, ["hygiene"])
    assert any(v["type"] == "unexpected_directory" and v["path"] == "docs/rogue/" for v in violations)


def test_format_expected_categories_section_empty():
    out = docs_structure._format_expected_categories_section([])
    assert "No categories declared" in out


def test_format_expected_categories_section_renders_rows():
    out = docs_structure._format_expected_categories_section(["hygiene", "security"])
    assert "| hygiene/ |" in out
    assert "| security/ |" in out
    assert "Must exist with README.md" in out


def test_format_violations_groups_by_type():
    violations = [
        {"type": "missing_directory", "path": "docs/x/", "message": "Missing directory: docs/x/"},
        {"type": "unexpected_file", "path": "docs/y.md", "message": "Unexpected file (not in index): docs/y.md"},
    ]
    out = docs_structure._format_violations_content(violations)
    assert "Found **2** violation(s)" in out
    assert "### Missing Directories" in out
    assert "### Unexpected Files" in out


def test_build_md_report_status_lines():
    data_clean = {"violations": [], "valid": True, "violation_count": 0, "expected_categories": ["hygiene"]}
    md_clean = docs_structure._build_md_report(data_clean, "2026-06-12 00:00:00 UTC")
    assert "✅ Documentation structure matches" in md_clean
    assert "✅ No violations found" in md_clean

    data_bad = {
        "violations": [{"type": "missing_directory", "path": "docs/x/", "message": "Missing directory: docs/x/"}],
        "valid": False,
        "violation_count": 1,
        "expected_categories": ["x"],
    }
    md_bad = docs_structure._build_md_report(data_bad, "2026-06-12 00:00:00 UTC")
    assert "❌ Documentation structure violations found" in md_bad
    assert "Missing directory: docs/x/" in md_bad


def test_run_clean_returns_zero_and_writes_both_reports(isolated_cwd, capsys):
    docs = Path("docs")
    _seed_index(docs, ["hygiene"])
    _seed_category(docs, "hygiene")
    rc = docs_structure.run()
    assert rc == 0
    assert docs_structure.REPORT_JSON.exists()
    assert docs_structure.REPORT_MD.exists()
    data = json.loads(docs_structure.REPORT_JSON.read_text())
    assert data["valid"] is True
    assert data["violation_count"] == 0
    assert data["expected_categories"] == ["hygiene"]


def test_run_flags_missing_category_directory(isolated_cwd):
    docs = Path("docs")
    _seed_index(docs, ["hygiene", "security"])
    _seed_category(docs, "hygiene")
    rc = docs_structure.run()
    assert rc == 1
    data = json.loads(docs_structure.REPORT_JSON.read_text())
    assert data["valid"] is False
    assert any(v["type"] == "missing_directory" for v in data["violations"])


def test_run_returns_one_when_docs_dir_missing(isolated_cwd, capsys):
    # No docs/ directory at all
    rc = docs_structure.run()
    assert rc == 1
    assert "docs/ directory not found" in capsys.readouterr().out


def test_run_returns_one_when_index_missing(isolated_cwd, capsys):
    Path("docs").mkdir()
    rc = docs_structure.run()
    assert rc == 1
    assert "docs/index.md not found" in capsys.readouterr().out
