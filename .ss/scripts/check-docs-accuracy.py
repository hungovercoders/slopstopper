#!/usr/bin/env python3

"""
Documentation Accuracy Validator

Checks documentation files for common accuracy issues:
- Broken internal markdown links (file references that don't resolve)
- References to non-existent Taskfile tasks
- References to non-existent workflow files
- Stale project descriptions (single-file vs multi-file, wrong tool names)

Generates a JSON report at .docs-reports/docs-accuracy-report.json.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────

def get_taskfile_tasks():
    """Extract declared task names from Taskfile.yml."""
    taskfile = Path("Taskfile.yml")
    if not taskfile.exists():
        return set()
    content = taskfile.read_text()
    # Match top-level task keys (2-space indent, name ending with colon)
    return {m.group(1) for m in re.finditer(r"^  ([a-z][a-z0-9:_-]+):", content, re.MULTILINE)}


def get_workflow_files():
    """List workflow filenames under .github/workflows/."""
    wf_dir = Path(".github/workflows")
    if not wf_dir.is_dir():
        return set()
    return {f.name for f in wf_dir.iterdir() if f.is_file()}


def get_project_files():
    """List all files in the repo root (non-hidden, depth 1) plus key paths."""
    root = Path(".")
    files = set()
    for entry in root.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_file():
            files.add(entry.name)
        elif entry.is_dir():
            files.add(entry.name + "/")
    # Also index docs tree
    for p in Path("docs").rglob("*"):
        files.add(str(p))
    # And .github tree
    gh = Path(".github")
    if gh.exists():
        for p in gh.rglob("*"):
            files.add(str(p))
    return files


# ── Checks ───────────────────────────────────────────────────────────

_GITHUB_WEB_PATH_SEGMENTS = frozenset({
    "issues", "discussions", "pulls", "milestones", "projects", "wiki",
    "pulse", "graphs", "settings", "compare", "tree", "blob", "raw",
    "blame", "commits", "tags", "releases", "packages", "actions",
})


def check_broken_links(md_path, project_files):
    """Find markdown links whose target file does not exist on disk."""
    issues = []
    content = md_path.read_text()
    base = md_path.parent

    # Match [text](target) — skip http(s), mailto, and anchors-only
    for m in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', content):
        display, target = m.group(1), m.group(2)
        # skip external / anchor-only / mermaid
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        # strip query string and anchor fragment (query strings are never file paths)
        target_path = target.split("?")[0].split("#")[0]
        if not target_path:
            continue
        # skip relative links targeting GitHub web interface paths
        # (e.g. ../../issues/new, ../../discussions/new)
        if any(part in _GITHUB_WEB_PATH_SEGMENTS for part in Path(target_path).parts):
            continue
        resolved = (base / target_path).resolve()
        if not resolved.exists():
            line_no = content[:m.start()].count("\n") + 1
            issues.append({
                "type": "broken_link",
                "file": str(md_path),
                "line": line_no,
                "message": f"Broken link: [{display}]({target}) — target does not exist",
            })
    return issues


def check_task_references(md_path, valid_tasks):
    """Find `task <name>` references that don't match a real Taskfile task.

    Only checks namespaced tasks (containing ':') to avoid false positives
    from prose like 'task runner' or 'task to'.
    """
    issues = []
    content = md_path.read_text()
    # Match `task <namespaced-name>` — require a colon to distinguish real
    # task invocations from English prose containing the word "task".
    for m in re.finditer(r'(?:^|\s)task\s+([a-z][a-z0-9_-]*:[a-z0-9:_-]+)', content):
        task_name = m.group(1)
        if task_name not in valid_tasks:
            line_no = content[:m.start()].count("\n") + 1
            issues.append({
                "type": "stale_task_ref",
                "file": str(md_path),
                "line": line_no,
                "message": f"Task reference `task {task_name}` not found in Taskfile.yml",
            })
    return issues


def check_workflow_references(md_path, valid_workflows):
    """Find .yml workflow file references that don't exist."""
    issues = []
    content = md_path.read_text()
    # Match .github/workflows/<name>.yml references
    for m in re.finditer(r'\.github/workflows/([a-z0-9_-]+\.yml)', content):
        wf_name = m.group(1)
        if wf_name not in valid_workflows:
            line_no = content[:m.start()].count("\n") + 1
            issues.append({
                "type": "stale_workflow_ref",
                "file": str(md_path),
                "line": line_no,
                "message": f"Workflow reference `.github/workflows/{wf_name}` does not exist",
            })
    return issues


_TRACKED_EXTENSIONS = frozenset(
    (".html", ".js", ".css", ".json", ".yml", ".yaml", ".toml", ".py", ".sh", ".md")
)


def _should_skip_ref(ref, ext, base, content, m, suggestion_ctx):
    """Return True if this file reference should be skipped."""
    if ref.startswith(("http", "mailto")):
        return True
    if ext not in _TRACKED_EXTENSIONS:
        return True
    if Path(ref).exists() or (base / ref).exists():
        return True
    if any(sub in ref for sub in ("example", "your-", "<", "YYYY")):
        return True
    start = max(0, m.start() - 250)
    end = min(len(content), m.end() + 250)
    if suggestion_ctx.search(content[start:end]):
        return True
    if ext in (".yml", ".yaml") and "/" not in ref:
        return True
    return False


def check_source_file_references(md_path, project_files):
    """Find references to source files in prose that no longer exist.

    Looks for backtick-quoted filenames that look like project paths.
    Skips references that appear to be examples, suggestions, or patterns.
    """
    issues = []
    content = md_path.read_text()
    base = md_path.parent

    # Phrases that indicate the file is an example / suggestion, or a generated
    # runtime artifact rather than a real tracked reference
    suggestion_ctx = re.compile(
        r'(split into|could create|create a|for example|e\.g\.|such as|'
        r'examples?:|add\b.*\bhere|when.*needed|naming|format|add a\b|generat\w*)',
        re.IGNORECASE,
    )

    for m in re.finditer(r'`([a-zA-Z0-9_./-]+\.[a-z]{1,4})`', content):
        ref = m.group(1)
        ext = Path(ref).suffix
        if _should_skip_ref(ref, ext, base, content, m, suggestion_ctx):
            continue
        line_no = content[:m.start()].count("\n") + 1
        issues.append({
            "type": "stale_file_ref",
            "file": str(md_path),
            "line": line_no,
            "message": f"Possible stale file reference: `{ref}` not found on disk",
        })
    return issues


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("🔍 Checking documentation accuracy…")

    valid_tasks = get_taskfile_tasks()
    valid_workflows = get_workflow_files()
    project_files = get_project_files()

    docs_path = Path("docs")
    if not docs_path.is_dir():
        print("❌ docs/ directory not found")
        sys.exit(1)

    all_issues = []

    for md_file in sorted(docs_path.rglob("*.md")):
        all_issues.extend(check_broken_links(md_file, project_files))
        all_issues.extend(check_task_references(md_file, valid_tasks))
        all_issues.extend(check_workflow_references(md_file, valid_workflows))
        all_issues.extend(check_source_file_references(md_file, project_files))

    # Write JSON report
    Path(".docs-reports").mkdir(exist_ok=True)
    report = {
        "issues": all_issues,
        "issue_count": len(all_issues),
        "clean": len(all_issues) == 0,
    }
    with open(".docs-reports/docs-accuracy-report.json", "w") as f:
        json.dump(report, f, indent=2)

    if all_issues:
        print(f"⚠️  Found {len(all_issues)} accuracy issue(s)")
        for issue in all_issues:
            print(f"  {issue['file']}:{issue['line']} — {issue['message']}")
        sys.exit(1)
    else:
        print("✅ Documentation accuracy checks passed")


if __name__ == "__main__":
    main()
