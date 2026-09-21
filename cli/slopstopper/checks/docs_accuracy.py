"""Documentation accuracy validator.

Ports .ss/scripts/check-docs-accuracy.py + generate-docs-accuracy-md.py.
Scans docs/**/*.md plus the four repo-root entry files (README.md,
AGENTS.md, CLAUDE.md, CONTRIBUTING.md) for four kinds of drift:

  - broken_link        — markdown link target missing on disk
  - stale_task_ref     — `task <namespace:name>` doesn't match Taskfile
  - stale_workflow_ref — .github/workflows/<file> doesn't exist
  - stale_file_ref     — backtick-quoted filepath not found on disk

Optionally scans more files, with only the checks that are precise for
them: `stale_task_ref` and `stale_workflow_ref` for markdown, and for
both markdown and HTML a fifth kind —

  - broken_repo_link   — a `github.com/<this repo>/blob|tree/<ref>/<path>`
                         link whose path does not exist

That is how a marketing page quoting a script that was deleted two
releases ago gets caught, which the docs/-only scan never could. The
relative-link and backtick-path checks are not applied outside docs/:
a skill or a site page describes an adopter's tree, not this one.

Configuration (.slopstopper.yml — all optional):

    hygiene:
      docs_accuracy:
        extra_paths: []   # repo-relative globs, e.g. [app/*.html, .claude/skills/**/*.md]

Writes a JSON report (machine-readable) and a Markdown report (human-
readable). Exit codes mirror the bash:

  0 — clean
  1 — issues OR docs/ missing
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from slopstopper import config, output
from slopstopper.badges import _detect_owner_repo

REPORT_DIR = Path(".ss/reports/docs")
REPORT_JSON = REPORT_DIR / "docs-accuracy-report.json"
REPORT_MD = REPORT_DIR / "docs-accuracy-report.md"

# Consumed by `slopstopper emit hygiene:docs-accuracy --target {pr-comment,issue}`.
# Discriminator matches the H1 of the report ("# 🔎 Documentation Accuracy Report")
# so the same bot comment is reused after the workflow flip. Issue title,
# labels, and follow-up string are byte-identical to the legacy block. The
# close behaviour is also driven by emit (`--on-pass=close`) since PR 1 of
# the issue-emission unification — close_comment matches the legacy YAML
# message so adopters see the same friendly recovery line.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "🔎 Documentation Accuracy",
    "issue_title": "🔎 Documentation Accuracy Issues",
    "issue_labels": ["documentation-accuracy", "documentation"],
    "issue_followup": "🔔 Documentation accuracy issues detected again",
    "issue_close_comment": "✅ Documentation accuracy checks now pass. Closing automatically.",
}

DOCS_DIR = Path("docs")
ROOT_ENTRY_FILES = ("README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md")

# Refs that look like file paths but represent something else:
_GITHUB_WEB_PATH_SEGMENTS = frozenset({
    "issues", "discussions", "pulls", "milestones", "projects", "wiki",
    "pulse", "graphs", "settings", "compare", "tree", "blob", "raw",
    "blame", "commits", "tags", "releases", "packages", "actions",
})

_TRACKED_EXTENSIONS = frozenset(
    (".html", ".js", ".css", ".json", ".yml", ".yaml", ".toml", ".py", ".sh", ".md")
)
_SKIP_REF_PREFIXES = ("http", "mailto", "/")
_PLACEHOLDER_SUBS = ("example", "your-", "<", "YYYY")

# Phrases that indicate a backtick-quoted file ref is an example or
# suggestion, not a real path. Used to suppress false positives in tutorial
# prose and "how to add a new check" instructions.
_SUGGESTION_CTX = re.compile(
    r'(split into|could create|create a|for example|e\.g\.|such as|'
    r'examples?:|add\b.*\bhere|when.*needed|naming|format|add a\b|generat\w*)',
    re.IGNORECASE,
)

_TASKFILE_TASK_RE = re.compile(r"^  ([a-z][a-z0-9:_-]+):", re.MULTILINE)
_MD_LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
# A leading backtick counts as a word boundary: docs write `task ss:x`,
# and requiring whitespace before `task` silently exempted every one.
# The trailing lookahead stops `task ss:hygiene:*` (a wildcard in prose)
# from half-matching as `ss:hygiene:`.
_TASK_REF_RE = re.compile(r'(?:^|[\s`])task\s+([a-z][a-z0-9_-]*:[a-z0-9:_-]+)(?![*:\w-])')
_WF_REF_RE = re.compile(r'\.github/workflows/([a-z0-9_.-]+\.(?:yml|md))')
_BACKTICK_FILE_RE = re.compile(r'`([a-zA-Z0-9_./-]+\.[a-z]{1,4})`')


def _get_taskfile_tasks() -> set[str]:
    tasks: set[str] = set()
    root = Path("Taskfile.yml")
    if root.exists():
        tasks |= {m.group(1) for m in _TASKFILE_TASK_RE.finditer(root.read_text())}
    ss = Path("Taskfile.ss.yml")
    if ss.exists():
        tasks |= {"ss:" + m.group(1) for m in _TASKFILE_TASK_RE.finditer(ss.read_text())}
    return tasks


def _get_workflow_files() -> set[str]:
    wf_dir = Path(".github/workflows")
    if not wf_dir.is_dir():
        return set()
    return {f.name for f in wf_dir.iterdir() if f.is_file()}


def _line_of(content: str, position: int) -> int:
    return content[:position].count("\n") + 1


def _check_broken_links(md_path: Path) -> list[dict]:
    issues: list[dict] = []
    content = md_path.read_text()
    base = md_path.parent
    for m in _MD_LINK_RE.finditer(content):
        display, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target_path = target.split("?")[0].split("#")[0]
        if not target_path:
            continue
        if any(part in _GITHUB_WEB_PATH_SEGMENTS for part in Path(target_path).parts):
            continue
        resolved = (base / target_path).resolve()
        if not resolved.exists():
            issues.append({
                "type": "broken_link",
                "file": str(md_path),
                "line": _line_of(content, m.start()),
                "message": f"Broken link: [{display}]({target}) — target does not exist",
            })
    return issues


def _check_task_references(md_path: Path, valid_tasks: set[str]) -> list[dict]:
    issues: list[dict] = []
    content = md_path.read_text()
    for m in _TASK_REF_RE.finditer(content):
        task_name = m.group(1)
        if task_name not in valid_tasks:
            issues.append({
                "type": "stale_task_ref",
                "file": str(md_path),
                "line": _line_of(content, m.start()),
                "message": f"Task reference `task {task_name}` not found in Taskfile.yml",
            })
    return issues


def _check_workflow_references(md_path: Path, valid_workflows: set[str]) -> list[dict]:
    issues: list[dict] = []
    content = md_path.read_text()
    for m in _WF_REF_RE.finditer(content):
        wf_name = m.group(1)
        if wf_name not in valid_workflows:
            issues.append({
                "type": "stale_workflow_ref",
                "file": str(md_path),
                "line": _line_of(content, m.start()),
                "message": f"Workflow reference `.github/workflows/{wf_name}` does not exist",
            })
    return issues


def _ref_is_placeholder_or_external(ref: str, ext: str) -> bool:
    if ref.startswith(_SKIP_REF_PREFIXES):
        return True
    if ext not in _TRACKED_EXTENSIONS:
        return True
    if any(sub in ref for sub in _PLACEHOLDER_SUBS):
        return True
    if ext in (".yml", ".yaml") and "/" not in ref:
        return True
    return False


def _should_skip_file_ref(ref: str, ext: str, base: Path, content: str, m: re.Match) -> bool:
    if _ref_is_placeholder_or_external(ref, ext):
        return True
    if Path(ref).exists() or (base / ref).exists():
        return True
    start = max(0, m.start() - 250)
    end = min(len(content), m.end() + 250)
    return bool(_SUGGESTION_CTX.search(content[start:end]))


def _check_source_file_references(md_path: Path) -> list[dict]:
    issues: list[dict] = []
    content = md_path.read_text()
    base = md_path.parent
    for m in _BACKTICK_FILE_RE.finditer(content):
        ref = m.group(1)
        ext = Path(ref).suffix
        if _should_skip_file_ref(ref, ext, base, content, m):
            continue
        issues.append({
            "type": "stale_file_ref",
            "file": str(md_path),
            "line": _line_of(content, m.start()),
            "message": f"Possible stale file reference: `{ref}` not found on disk",
        })
    return issues


def _collect_targets() -> list[Path]:
    targets = sorted(DOCS_DIR.rglob("*.md"))
    for entry in ROOT_ENTRY_FILES:
        entry_path = Path(entry)
        if entry_path.exists():
            targets.append(entry_path)
    return targets


def _collect_extra_targets() -> list[Path]:
    """Files named by `hygiene.docs_accuracy.extra_paths`, deduplicated, in order."""
    seen: set[Path] = set()
    out: list[Path] = []
    raw = config.get("hygiene.docs_accuracy.extra_paths", []) or []
    patterns = raw if isinstance(raw, list) else [raw]
    for pattern in patterns:
        for hit in sorted(Path(".").glob(str(pattern).strip())):
            if hit.is_file() and hit not in seen:
                seen.add(hit)
                out.append(hit)
    return out


# `https://github.com/<owner>/<repo>/blob|tree/<ref>/<path>` — the shape
# every "View source →" link on a site takes. Only links into *this* repo
# are checked; anyone else's paths are not ours to verify.
_REPO_LINK_RE = re.compile(
    r'https://github\.com/([^/"\s]+)/([^/"\s]+)/(?:blob|tree)/[^/"\s]+/([^"\s#?)<]+)'
)


def _check_repo_links(path: Path, owner: str, repo: str) -> list[dict]:
    issues: list[dict] = []
    content = path.read_text(errors="replace")
    for m in _REPO_LINK_RE.finditer(content):
        link_owner, link_repo, target = m.groups()
        if (link_owner, link_repo.removesuffix(".git")) != (owner, repo):
            continue
        target = target.rstrip("/")
        if Path(target).exists():
            continue
        issues.append({
            "type": "broken_repo_link",
            "file": str(path),
            "line": _line_of(content, m.start()),
            "message": f"Link into this repo points at `{target}`, which does not exist",
        })
    return issues


def _collect_all_issues(targets: list[Path], valid_tasks: set[str], valid_workflows: set[str]) -> list[dict]:
    issues: list[dict] = []
    for md_file in targets:
        issues += _check_broken_links(md_file)
        issues += _check_task_references(md_file, valid_tasks)
        issues += _check_workflow_references(md_file, valid_workflows)
        issues += _check_source_file_references(md_file)
    return issues


def _collect_extra_issues(
    extra: list[Path], valid_tasks: set[str], valid_workflows: set[str]
) -> list[dict]:
    """Route each extra file to the checks that are precise for it.

    Files outside docs/ get only the checks whose references name a real
    target in *this* repo: `task ss:…`, `.github/workflows/…`, and links
    into this repo on github.com. They deliberately do not get the
    relative-link or backtick-path checks — a skill or a marketing page
    describes an adopter's tree, so `vercel.json` or `[category/](category/)`
    in it is an example, not a claim about this checkout, and flagging
    those would train people to ignore the check.
    """
    supported = {".md", ".html", ".htm"}
    files = [p for p in extra if p.suffix.lower() in supported]
    issues: list[dict] = []
    for path in files:
        if path.suffix.lower() == ".md":
            issues += _check_task_references(path, valid_tasks)
            issues += _check_workflow_references(path, valid_workflows)
    if not files:
        return issues
    owner, repo = _detect_owner_repo()
    if not owner or not repo:
        output.warn(
            "could not detect this repo's owner/name (no $GITHUB_REPOSITORY, no github.com "
            f"remote) — links into this repo in {len(files)} extra file(s) were not checked"
        )
        return issues
    for path in files:
        issues += _check_repo_links(path, owner, repo)
    return issues


def _generated_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


_TYPE_LABELS = {
    "broken_link": "Broken Internal Links",
    "stale_task_ref": "Stale Taskfile References",
    "stale_workflow_ref": "Stale Workflow References",
    "stale_file_ref": "Possible Stale File References",
    "broken_repo_link": "Broken Links Into This Repository",
}


def _build_md_report(data: dict, generated_at: str) -> str:
    issues = data.get("issues", [])
    is_clean = data.get("clean", True)

    lines = [
        "# 🔎 Documentation Accuracy Report",
        "",
        f"**Generated:** {generated_at}",
        "",
        "## Status",
        "",
    ]
    if is_clean:
        lines.append("✅ All documentation accuracy checks passed — no stale references detected.")
    else:
        lines.append(f"⚠️ Found **{len(issues)}** accuracy issue(s) that may need attention.")

    lines += ["", "## Issues", ""]

    if not issues:
        lines.append("No issues found.")
    else:
        by_type: dict[str, list[dict]] = {}
        for issue in issues:
            by_type.setdefault(issue["type"], []).append(issue)
        for itype, group in by_type.items():
            label = _TYPE_LABELS.get(itype, itype)
            lines.append(f"### {label}")
            lines.append("")
            for item in group:
                lines.append(f"- **{item['file']}** (line {item['line']}): {item['message']}")
            lines.append("")

    lines += [
        "## How to Fix",
        "",
        "1. Review each issue above.",
        "2. Update the referenced docs to match the current project state.",
        "3. Run `task ss:hygiene:docs-accuracy` locally to verify fixes.",
        "",
    ]
    return "\n".join(lines) + "\n"


def run(_args: list[str] | None = None) -> int:
    output.running("Checking documentation accuracy…")

    if not DOCS_DIR.is_dir():
        output.error("docs/ directory not found")
        return 1

    valid_tasks = _get_taskfile_tasks()
    valid_workflows = _get_workflow_files()
    targets = _collect_targets()
    issues = _collect_all_issues(targets, valid_tasks, valid_workflows)
    issues += _collect_extra_issues(_collect_extra_targets(), valid_tasks, valid_workflows)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "issues": issues,
        "issue_count": len(issues),
        "clean": len(issues) == 0,
    }
    REPORT_JSON.write_text(json.dumps(data, indent=2))
    REPORT_MD.write_text(_build_md_report(data, _generated_at()))

    if issues:
        output.warn(f"Found {len(issues)} accuracy issue(s)")
        for issue in issues:
            output._emit(f"  {issue['file']}:{issue['line']} — {issue['message']}")
        output.footer(REPORT_DIR, [REPORT_MD.name])
        return 1
    output.success("Documentation accuracy checks passed")
    output.footer(REPORT_DIR, [REPORT_MD.name])
    return 0
