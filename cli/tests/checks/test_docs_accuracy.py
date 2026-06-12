"""Tests for the hygiene:docs-accuracy check."""

from __future__ import annotations

import json
from pathlib import Path

from slopstopper.checks import docs_accuracy


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def test_get_taskfile_tasks_reads_both_files(isolated_cwd):
    _write(Path("Taskfile.yml"), "version: '3'\ntasks:\n  build:\n    cmds: []\n")
    _write(
        Path("Taskfile.ss.yml"),
        "version: '3'\ntasks:\n  hygiene:lint:\n    cmds: []\n  security:sast:\n    cmds: []\n",
    )
    tasks = docs_accuracy._get_taskfile_tasks()
    assert "build" in tasks
    assert "ss:hygiene:lint" in tasks
    assert "ss:security:sast" in tasks


def test_get_workflow_files_lists_files_only(isolated_cwd):
    wf = isolated_cwd / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ss-x.yml").write_text("name: x")
    (wf / "ss-y.lock.yml").write_text("name: y")
    (wf / "subdir").mkdir()
    assert docs_accuracy._get_workflow_files() == {"ss-x.yml", "ss-y.lock.yml"}


def test_check_broken_links_flags_missing_target(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(md, "See [here](missing.md)\n")
    issues = docs_accuracy._check_broken_links(md)
    assert len(issues) == 1
    assert issues[0]["type"] == "broken_link"
    assert "missing.md" in issues[0]["message"]


def test_check_broken_links_skips_external_and_anchors(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(
        md,
        "[ext](https://example.com)\n[m](mailto:a@b)\n[a](#anchor)\n[q](file.md?x=1)\n",
    )
    # file.md doesn't exist; but http/mailto/anchor are all skipped, and the
    # query-string strip means file.md gets checked → it should fail.
    issues = docs_accuracy._check_broken_links(md)
    assert all(i["type"] == "broken_link" for i in issues)
    assert any("file.md" in i["message"] for i in issues)
    assert not any("https://" in i["message"] for i in issues)


def test_check_broken_links_skips_github_web_paths(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(md, "[file an issue](../../issues/new)\n[PR](../../pulls/1)\n")
    assert docs_accuracy._check_broken_links(md) == []


def test_check_broken_links_resolves_relative(isolated_cwd):
    docs = isolated_cwd / "docs"
    _write(docs / "x.md", "[t](other.md)\n")
    (docs / "other.md").write_text("hi\n")
    assert docs_accuracy._check_broken_links(docs / "x.md") == []


def test_check_task_references_flags_unknown(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    # Regex requires whitespace (or BOL) before "task" — backtick adjacency
    # is deliberately not matched to avoid false-positives on inline code.
    _write(md, "Run task ss:nonexistent:check to verify.\n")
    issues = docs_accuracy._check_task_references(md, {"ss:hygiene:lint"})
    assert len(issues) == 1
    assert issues[0]["type"] == "stale_task_ref"
    assert "ss:nonexistent:check" in issues[0]["message"]


def test_check_task_references_ignores_unnamespaced(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(md, "this is task runner adjacent prose\n")
    assert docs_accuracy._check_task_references(md, set()) == []


def test_check_workflow_references_flags_missing(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(md, "See .github/workflows/nope.yml for details.\n")
    issues = docs_accuracy._check_workflow_references(md, {"present.yml"})
    assert len(issues) == 1
    assert issues[0]["type"] == "stale_workflow_ref"


def test_check_workflow_references_passes_existing(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(md, "See .github/workflows/ok.yml for details.\n")
    assert docs_accuracy._check_workflow_references(md, {"ok.yml"}) == []


def test_ref_is_placeholder_or_external_flags_examples():
    assert docs_accuracy._ref_is_placeholder_or_external("https://x.com", ".com") is True
    assert docs_accuracy._ref_is_placeholder_or_external("example.py", ".py") is True
    assert docs_accuracy._ref_is_placeholder_or_external("your-repo.yml", ".yml") is True
    assert docs_accuracy._ref_is_placeholder_or_external("setup.bin", ".bin") is True
    # Bare yml is treated as tutorial prose, not a real reference.
    assert docs_accuracy._ref_is_placeholder_or_external("config.yml", ".yml") is True


def test_ref_is_placeholder_or_external_lets_real_paths_through():
    assert docs_accuracy._ref_is_placeholder_or_external("docs/x.md", ".md") is False
    assert docs_accuracy._ref_is_placeholder_or_external("path/to/.yml", ".yml") is False


def test_check_source_file_references_flags_missing(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(md, "The script `.ss/scripts/missing.py` does X.\n")
    issues = docs_accuracy._check_source_file_references(md)
    assert len(issues) == 1
    assert issues[0]["type"] == "stale_file_ref"


def test_check_source_file_references_suppresses_via_suggestion_context(isolated_cwd):
    md = isolated_cwd / "docs" / "x.md"
    _write(md, "For example, `something.py` could be created.\n")
    assert docs_accuracy._check_source_file_references(md) == []


def test_build_md_report_clean():
    md = docs_accuracy._build_md_report(
        {"issues": [], "issue_count": 0, "clean": True}, "2026-06-12 00:00:00 UTC"
    )
    assert "✅" in md
    assert "No issues found" in md


def test_build_md_report_with_issues_groups_by_type():
    data = {
        "issues": [
            {"type": "broken_link", "file": "docs/a.md", "line": 5, "message": "X"},
            {"type": "stale_task_ref", "file": "docs/b.md", "line": 10, "message": "Y"},
        ],
        "issue_count": 2,
        "clean": False,
    }
    md = docs_accuracy._build_md_report(data, "2026-06-12 00:00:00 UTC")
    assert "Found **2** accuracy issue(s)" in md
    assert "### Broken Internal Links" in md
    assert "### Stale Taskfile References" in md
    assert "docs/a.md" in md and "(line 5)" in md


def test_run_clean_returns_zero(isolated_cwd):
    _write(Path("docs/index.md"), "# docs\n")
    rc = docs_accuracy.run()
    assert rc == 0
    assert docs_accuracy.REPORT_JSON.exists()
    assert docs_accuracy.REPORT_MD.exists()
    data = json.loads(docs_accuracy.REPORT_JSON.read_text())
    assert data["clean"] is True
    assert data["issue_count"] == 0


def test_run_returns_one_when_docs_missing(isolated_cwd, capsys):
    rc = docs_accuracy.run()
    assert rc == 1
    assert "docs/ directory not found" in capsys.readouterr().out


def test_run_flags_broken_link(isolated_cwd):
    _write(Path("docs/x.md"), "See [gone](does-not-exist.md)\n")
    rc = docs_accuracy.run()
    assert rc == 1
    data = json.loads(docs_accuracy.REPORT_JSON.read_text())
    assert data["clean"] is False
    assert any(i["type"] == "broken_link" for i in data["issues"])
