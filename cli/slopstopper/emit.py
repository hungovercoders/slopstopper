"""GitHub PR-comment and issue emission for checks.

Centralises the find-or-create logic that lives, today, as duplicated
`actions/github-script@v7` blocks in every `ss-*-check.yml` workflow.
The plan called this out as the load-bearing simplification — once the
emit logic lives here, workflows shrink from ~50 lines of YAML +
embedded JS to a single shell line:

  - run: slopstopper run hygiene:docs-size
  - run: slopstopper emit hygiene:docs-size --target pr-comment
    if: github.event_name == 'pull_request'
  - run: slopstopper emit hygiene:docs-size --target issue
    if: github.event_name == 'push' && steps.check.outcome == 'failure'

Subprocess-invokes the `gh` CLI — already on every GitHub Actions
runner and already authed via $GITHUB_TOKEN. Same licensing-boundary
pattern as the other external tools (gitleaks, trivy, semgrep, zap):
slopstopper-cli wheel ships zero gh code.

Each check that wants to emit declares a META dict beside its `run()`:

    META = {
        "report_path": ".ss/reports/.../*.md",
        "comment_discriminator": "📚 ...",   # substring uniquely on the bot's PR comment
        "issue_title": "📚 ... Exceeds Thresholds",
        "issue_labels": ["...", "maintenance"],
        "issue_followup": "🔔 Thresholds exceeded again in commit",
        "issue_close_comment": "✅ ... now within thresholds. Closing automatically.",  # optional; used by `emit --on-pass=close`
    }

The brand label `slopstopper` is auto-prepended to `issue_labels` so every
emitted issue can be discovered with `gh issue list --label slopstopper`.
Bodies also gain a hidden HTML-comment marker `<!-- slopstopper:check=<name> -->`
in the footer for machine-readable dedup (used by
`ss-workflow-failure-issue.yml`'s deduplication).

PR-comment update path: `gh api PATCH .../issues/comments/{id}` —
`gh` doesn't have a direct edit-comment command.
Issue path: `gh issue list | gh issue {create,edit,comment,close}`.

Note: issue bodies are bot-managed. `_update_issue_body` overwrites the
whole body on every re-emit, so the marker stays stable but hand-edited
maintainer notes in the body get wiped. Track notes as issue comments
instead.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _gh_available() -> bool:
    return shutil.which("gh") is not None


def _repo_slug() -> str | None:
    """GitHub-Actions-supplied $GITHUB_REPOSITORY = owner/name."""
    return os.environ.get("GITHUB_REPOSITORY")


def _pr_number_from_event() -> int | None:
    """Read the PR number from the workflow event payload.

    Works for `pull_request` triggers. Returns None on push / workflow_dispatch.
    """
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        return None
    try:
        event = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    pr = event.get("pull_request")
    if isinstance(pr, dict) and isinstance(pr.get("number"), int):
        return pr["number"]
    return None


def _gh(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run `gh` with stdout/stderr passthrough (or captured)."""
    cmd = ["gh", *args]
    if capture:
        return subprocess.run(cmd, check=False, capture_output=True, text=True)
    return subprocess.run(cmd, check=False)


# ── PR comment emission ──────────────────────────────────────────


def _list_pr_comments(repo: str, pr: int) -> list[dict]:
    result = _gh("api", f"repos/{repo}/issues/{pr}/comments", capture=True)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _find_existing_pr_comment(comments: list[dict], discriminator: str) -> int | None:
    """Return the comment id whose body contains the discriminator and was posted by a bot."""
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        user = comment.get("user") or {}
        if user.get("type") != "Bot":
            continue
        body = comment.get("body") or ""
        if discriminator in body:
            cid = comment.get("id")
            if isinstance(cid, int):
                return cid
    return None


def _update_pr_comment(repo: str, comment_id: int, body_path: Path) -> int:
    """gh api PATCH .../issues/comments/<id> -F body=@<path>."""
    result = _gh(
        "api", "-X", "PATCH",
        f"repos/{repo}/issues/comments/{comment_id}",
        "-F", f"body=@{body_path}",
        capture=True,
    )
    return result.returncode


def _create_pr_comment(pr: int, body_path: Path) -> int:
    result = _gh("pr", "comment", str(pr), "--body-file", str(body_path))
    return result.returncode


def emit_pr_comment(report_path: Path, discriminator: str) -> int:
    """Post the report as a PR comment, updating any prior bot comment with the same discriminator."""
    if not _gh_available():
        print("❌ gh CLI is not available — needed for --target pr-comment", file=sys.stderr)
        return 1
    if not report_path.exists():
        print(f"❌ Report not found at {report_path}", file=sys.stderr)
        return 1

    repo = _repo_slug()
    pr = _pr_number_from_event()
    if not repo:
        print("❌ $GITHUB_REPOSITORY is not set", file=sys.stderr)
        return 1
    if pr is None:
        print("❌ No PR detected from the event payload — skipping PR comment", file=sys.stderr)
        return 1

    comments = _list_pr_comments(repo, pr)
    existing = _find_existing_pr_comment(comments, discriminator)
    if existing is not None:
        print(f"↻ Updating existing PR comment {existing}")
        return _update_pr_comment(repo, existing, report_path)
    print(f"+ Creating new PR comment on #{pr}")
    return _create_pr_comment(pr, report_path)


# ── Issue emission ───────────────────────────────────────────────


_BRAND_LABEL = "slopstopper"


def _augment_labels(labels: list[str]) -> list[str]:
    """Prepend the slopstopper brand label if not already present.

    Idempotent — safe to call repeatedly. Single insertion point so every
    open/close path uses the same label set for dedup.
    """
    if _BRAND_LABEL in labels:
        return labels
    return [_BRAND_LABEL, *labels]


def _find_existing_issue(labels: list[str]) -> int | None:
    """Return the first open issue number that has every label."""
    label_args: list[str] = []
    for lbl in labels:
        label_args += ["--label", lbl]
    result = _gh(
        "issue", "list",
        "--state", "open",
        *label_args,
        "--json", "number",
        capture=True,
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if isinstance(first, dict) and isinstance(first.get("number"), int):
        return first["number"]
    return None


def _create_issue(title: str, body_path: Path, labels: list[str]) -> int:
    cmd: list[str] = ["issue", "create", "--title", title, "--body-file", str(body_path)]
    for lbl in labels:
        cmd += ["--label", lbl]
    return _gh(*cmd).returncode


def _update_issue_body(number: int, body_path: Path) -> int:
    return _gh("issue", "edit", str(number), "--body-file", str(body_path)).returncode


def _comment_issue(number: int, body: str) -> int:
    return _gh("issue", "comment", str(number), "--body", body).returncode


def _commit_sha() -> str:
    return os.environ.get("GITHUB_SHA", "")


def emit_issue(
    report_path: Path,
    title: str,
    labels: list[str],
    followup: str,
    *,
    check_name: str | None = None,
) -> int:
    """Create a new issue with the report, or update the existing one and post a follow-up comment.

    The body is the report content with a `Commit: <sha>` footer and, when
    `check_name` is provided, a hidden `<!-- slopstopper:check=... -->`
    marker. Labels are augmented with the `slopstopper` brand label.
    """
    if not _gh_available():
        print("❌ gh CLI is not available — needed for --target issue", file=sys.stderr)
        return 1
    if not report_path.exists():
        print(f"❌ Report not found at {report_path}", file=sys.stderr)
        return 1

    labels = _augment_labels(labels)
    sha = _commit_sha()
    body = report_path.read_text()

    footer_lines: list[str] = []
    if sha:
        footer_lines.append(f"*Commit: {sha}*")
    if check_name:
        footer_lines.append(f"<!-- slopstopper:check={check_name} -->")
    footer = ("\n\n---\n" + "\n".join(footer_lines) + "\n") if footer_lines else "\n"
    body_with_footer = body + footer

    body_path = report_path.with_suffix(".issue-body.md")
    body_path.write_text(body_with_footer)

    existing = _find_existing_issue(labels)
    if existing is not None:
        print(f"↻ Updating existing issue #{existing}")
        rc = _update_issue_body(existing, body_path)
        if rc == 0 and sha:
            _comment_issue(existing, f"{followup} {sha}")
        return rc
    print("+ Creating new issue")
    return _create_issue(title, body_path, labels)


# ── issue close ──────────────────────────────────────────────────


_DEFAULT_CLOSE_COMMENT = "✅ Check is now passing on `main`. Closing automatically."


def _close_issue(labels: list[str], close_comment: str) -> int:
    """Comment + close any open issue matching `labels`. No-op if none exists.

    Used by `emit --on-pass=close` as the post-success twin of
    `emit_issue`'s post-failure open path. Same label-intersection dedup
    (including the `slopstopper` brand label) via `_find_existing_issue`,
    so a check only ever closes the issue it would have re-opened.
    """
    if not _gh_available():
        print("❌ gh CLI is not available — needed for --on-pass=close", file=sys.stderr)
        return 1
    labels = _augment_labels(labels)
    existing = _find_existing_issue(labels)
    if existing is None:
        print("· No open issue to close")
        return 0
    print(f"× Closing issue #{existing}")
    rc = _comment_issue(existing, close_comment)
    if rc != 0:
        return rc
    return _gh("issue", "close", str(existing)).returncode


# ── public dispatcher ────────────────────────────────────────────


def emit(
    target: str,
    meta: dict,
    *,
    check_name: str | None = None,
    on_pass: str | None = None,
) -> int:
    """Route --target {pr-comment, issue} to the corresponding emitter.

    meta is the check's META dict (see module docstring). check_name is
    the `category:name` identifier used in the issue body's brand marker.
    on_pass='close' (only valid with target='issue') flips the issue
    branch from open/update to comment-and-close — the post-success
    twin of the post-failure open path.
    """
    report_path = Path(meta["report_path"])
    if target == "pr-comment":
        return emit_pr_comment(report_path, meta["comment_discriminator"])
    if target == "issue":
        if on_pass == "close":
            return _close_issue(
                meta["issue_labels"],
                meta.get("issue_close_comment", _DEFAULT_CLOSE_COMMENT),
            )
        return emit_issue(
            report_path,
            meta["issue_title"],
            meta["issue_labels"],
            meta["issue_followup"],
            check_name=check_name,
        )
    print(f"❌ Unknown emit target: {target!r}", file=sys.stderr)
    return 2
