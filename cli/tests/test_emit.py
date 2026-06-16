"""Tests for slopstopper.emit — PR comment + issue emission via gh CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from slopstopper import emit


SAMPLE_META = {
    "report_path": "report.md",
    "comment_discriminator": "📚 Test Report",
    "issue_title": "📚 Test Thresholds Exceeded",
    "issue_labels": ["test-label", "maintenance"],
    "issue_followup": "🔔 Test thresholds exceeded again in commit",
}


# ── helpers ──────────────────────────────────────────────────────


def test_gh_available_via_which(monkeypatch):
    monkeypatch.setattr(emit.shutil, "which", lambda _: "/usr/bin/gh")
    assert emit._gh_available() is True
    monkeypatch.setattr(emit.shutil, "which", lambda _: None)
    assert emit._gh_available() is False


def test_repo_slug_reads_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    assert emit._repo_slug() == "owner/repo"


def test_repo_slug_none_when_unset(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert emit._repo_slug() is None


def test_pr_number_from_event_reads_payload(monkeypatch, tmp_path):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 42}}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert emit._pr_number_from_event() == 42


def test_pr_number_from_event_none_for_push(monkeypatch, tmp_path):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"ref": "refs/heads/main"}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert emit._pr_number_from_event() is None


def test_pr_number_from_event_none_when_path_unset(monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    assert emit._pr_number_from_event() is None


def test_pr_number_from_event_handles_malformed_json(monkeypatch, tmp_path):
    event = tmp_path / "event.json"
    event.write_text("not json")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert emit._pr_number_from_event() is None


# ── PR comment ───────────────────────────────────────────────────


def test_find_existing_pr_comment_matches_bot_discriminator():
    comments = [
        {"id": 1, "user": {"type": "User"}, "body": "📚 Test Report (human-typed)"},
        {"id": 2, "user": {"type": "Bot"}, "body": "Some other bot comment"},
        {"id": 3, "user": {"type": "Bot"}, "body": "📚 Test Report\nfull body…"},
    ]
    assert emit._find_existing_pr_comment(comments, "📚 Test Report") == 3


def test_find_existing_pr_comment_returns_none_when_no_match():
    comments = [{"id": 1, "user": {"type": "Bot"}, "body": "different content"}]
    assert emit._find_existing_pr_comment(comments, "missing") is None


def test_emit_pr_comment_fails_when_gh_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(emit, "_gh_available", lambda: False)
    rc = emit.emit_pr_comment(Path("report.md"), "discrim")
    assert rc == 1
    assert "gh CLI is not available" in capsys.readouterr().err


def test_emit_pr_comment_fails_when_report_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    rc = emit.emit_pr_comment(Path("nonexistent.md"), "discrim")
    assert rc == 1
    assert "Report not found" in capsys.readouterr().err


def test_emit_pr_comment_fails_when_no_pr_number(monkeypatch, isolated_cwd, capsys):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_repo_slug", lambda: "owner/repo")
    monkeypatch.setattr(emit, "_pr_number_from_event", lambda: None)
    rc = emit.emit_pr_comment(Path("report.md"), "discrim")
    assert rc == 1
    assert "No PR detected" in capsys.readouterr().err


def test_emit_pr_comment_creates_new_when_no_existing(monkeypatch, isolated_cwd, capsys):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_repo_slug", lambda: "owner/repo")
    monkeypatch.setattr(emit, "_pr_number_from_event", lambda: 99)
    monkeypatch.setattr(emit, "_list_pr_comments", lambda r, p: [])

    captured: dict = {}

    def fake_gh(*args, capture=False):
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(emit, "_gh", fake_gh)
    rc = emit.emit_pr_comment(Path("report.md"), "discrim")
    assert rc == 0
    assert "pr" in captured["args"] and "comment" in captured["args"]
    out = capsys.readouterr().out
    assert "Creating new PR comment on #99" in out


def test_emit_pr_comment_updates_existing(monkeypatch, isolated_cwd, capsys):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_repo_slug", lambda: "owner/repo")
    monkeypatch.setattr(emit, "_pr_number_from_event", lambda: 99)
    monkeypatch.setattr(
        emit, "_list_pr_comments",
        lambda r, p: [{"id": 555, "user": {"type": "Bot"}, "body": "📚 Test Report\nold body"}],
    )

    captured: dict = {}

    def fake_gh(*args, capture=False):
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(emit, "_gh", fake_gh)
    rc = emit.emit_pr_comment(Path("report.md"), "📚 Test Report")
    assert rc == 0
    assert "PATCH" in captured["args"]
    assert "repos/owner/repo/issues/comments/555" in captured["args"]
    out = capsys.readouterr().out
    assert "Updating existing PR comment 555" in out


# ── issue ────────────────────────────────────────────────────────


def test_find_existing_issue_returns_first_number(monkeypatch):
    def fake_gh(*args, capture=False):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps([{"number": 7}, {"number": 8}]),
            stderr="",
        )

    monkeypatch.setattr(emit, "_gh", fake_gh)
    assert emit._find_existing_issue(["test-label"]) == 7


def test_find_existing_issue_returns_none_on_empty(monkeypatch):
    monkeypatch.setattr(
        emit, "_gh",
        lambda *a, capture=False: subprocess.CompletedProcess(a, 0, stdout="[]", stderr=""),
    )
    assert emit._find_existing_issue(["test-label"]) is None


def test_find_existing_issue_returns_none_on_gh_failure(monkeypatch):
    monkeypatch.setattr(
        emit, "_gh",
        lambda *a, capture=False: subprocess.CompletedProcess(a, 1, stdout="", stderr="error"),
    )
    assert emit._find_existing_issue(["test-label"]) is None


def test_emit_issue_creates_new(monkeypatch, isolated_cwd, capsys):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: None)
    monkeypatch.setenv("GITHUB_SHA", "abc123")

    captured: dict = {}

    def fake_gh(*args, capture=False):
        captured.setdefault("calls", []).append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(emit, "_gh", fake_gh)
    rc = emit.emit_issue(
        Path("report.md"),
        "Test Title",
        ["test-label"],
        "🔔 followup",
    )
    assert rc == 0
    call = captured["calls"][0]
    assert "issue" in call and "create" in call
    assert "--title" in call and "Test Title" in call
    # Body file should contain the report content + sha footer
    body_file = next(arg for arg in call if "issue-body" in str(arg))
    body_text = Path(body_file).read_text()
    assert "body" in body_text
    assert "abc123" in body_text


def test_emit_issue_updates_existing_and_comments(monkeypatch, isolated_cwd, capsys):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: 42)
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")

    captured: dict = {}

    def fake_gh(*args, capture=False):
        captured.setdefault("calls", []).append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(emit, "_gh", fake_gh)
    rc = emit.emit_issue(
        Path("report.md"),
        "Test Title",
        ["test-label"],
        "🔔 followup",
    )
    assert rc == 0
    edit_call = captured["calls"][0]
    assert "edit" in edit_call and "42" in edit_call
    comment_call = captured["calls"][1]
    assert "comment" in comment_call and "42" in comment_call
    assert any("deadbeef" in str(a) for a in comment_call)


def test_emit_issue_fails_when_gh_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(emit, "_gh_available", lambda: False)
    rc = emit.emit_issue(Path("nope.md"), "T", ["L"], "F")
    assert rc == 1
    assert "gh CLI is not available" in capsys.readouterr().err


def test_emit_issue_prepends_slopstopper_label(monkeypatch, isolated_cwd):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    captured: dict = {}

    def fake_find(labels):
        captured["find_labels"] = list(labels)
        return None

    def fake_create(title, body_path, labels):
        captured["create_labels"] = list(labels)
        return 0

    monkeypatch.setattr(emit, "_find_existing_issue", fake_find)
    monkeypatch.setattr(emit, "_create_issue", fake_create)
    rc = emit.emit_issue(Path("report.md"), "T", ["sast", "security"], "F")
    assert rc == 0
    assert captured["find_labels"] == ["slopstopper", "sast", "security"]
    assert captured["create_labels"] == ["slopstopper", "sast", "security"]


def test_emit_issue_does_not_duplicate_slopstopper_label(monkeypatch, isolated_cwd):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    captured: dict = {}

    def fake_create(title, body_path, labels):
        captured["create_labels"] = list(labels)
        return 0

    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: None)
    monkeypatch.setattr(emit, "_create_issue", fake_create)
    rc = emit.emit_issue(Path("report.md"), "T", ["slopstopper", "sast"], "F")
    assert rc == 0
    assert captured["create_labels"].count("slopstopper") == 1


def test_emit_issue_writes_marker_when_check_name_provided(monkeypatch, isolated_cwd):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: None)
    monkeypatch.setenv("GITHUB_SHA", "abc123")

    captured: dict = {}

    def fake_create(title, body_path, labels):
        captured["body"] = Path(body_path).read_text()
        return 0

    monkeypatch.setattr(emit, "_create_issue", fake_create)
    rc = emit.emit_issue(
        Path("report.md"),
        "T",
        ["test-label"],
        "F",
        check_name="hygiene:docs-size",
    )
    assert rc == 0
    assert "<!-- slopstopper:check=hygiene:docs-size -->" in captured["body"]
    assert "*Commit: abc123*" in captured["body"]


def test_emit_issue_omits_marker_when_check_name_none(monkeypatch, isolated_cwd):
    Path("report.md").write_text("body")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: None)
    monkeypatch.setenv("GITHUB_SHA", "abc123")

    captured: dict = {}

    def fake_create(title, body_path, labels):
        captured["body"] = Path(body_path).read_text()
        return 0

    monkeypatch.setattr(emit, "_create_issue", fake_create)
    rc = emit.emit_issue(Path("report.md"), "T", ["test-label"], "F")
    assert rc == 0
    assert "slopstopper:check" not in captured["body"]


def test_emit_issue_marker_idempotent_on_update(monkeypatch, isolated_cwd):
    """Re-emitting on a re-failure regenerates the footer fresh from the report —
    the marker appears exactly once, never duplicated."""
    Path("report.md").write_text("body content")
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: 42)
    monkeypatch.setenv("GITHUB_SHA", "abc123")

    captured: dict = {}

    def fake_update(number, body_path):
        captured.setdefault("bodies", []).append(Path(body_path).read_text())
        return 0

    monkeypatch.setattr(emit, "_update_issue_body", fake_update)
    monkeypatch.setattr(emit, "_comment_issue", lambda n, b: 0)

    # Emit twice — the second call must not produce a body with two markers.
    for _ in range(2):
        emit.emit_issue(
            Path("report.md"),
            "T",
            ["test-label"],
            "F",
            check_name="hygiene:docs-size",
        )

    for body in captured["bodies"]:
        assert body.count("<!-- slopstopper:check=hygiene:docs-size -->") == 1


# ── issue close ──────────────────────────────────────────────────


def test_close_issue_comments_and_closes_when_match(monkeypatch, capsys):
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: 77)

    captured: dict = {}

    def fake_gh(*args, capture=False):
        captured.setdefault("calls", []).append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(emit, "_gh", fake_gh)
    rc = emit._close_issue(["test-label"], "✅ now passing")
    assert rc == 0
    comment_call = captured["calls"][0]
    assert "comment" in comment_call and "77" in comment_call
    assert "✅ now passing" in comment_call
    close_call = captured["calls"][1]
    assert "close" in close_call and "77" in close_call
    assert "Closing issue #77" in capsys.readouterr().out


def test_close_issue_noops_when_no_match(monkeypatch, capsys):
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    monkeypatch.setattr(emit, "_find_existing_issue", lambda labels: None)

    def fake_gh(*args, capture=False):
        raise AssertionError(f"_gh should not be called when no open issue, got {args}")

    monkeypatch.setattr(emit, "_gh", fake_gh)
    rc = emit._close_issue(["test-label"], "✅ now passing")
    assert rc == 0
    assert "No open issue to close" in capsys.readouterr().out


def test_close_issue_fails_when_gh_missing(monkeypatch, capsys):
    monkeypatch.setattr(emit, "_gh_available", lambda: False)
    rc = emit._close_issue(["test-label"], "✅ now passing")
    assert rc == 1
    assert "gh CLI is not available" in capsys.readouterr().err


def test_close_issue_searches_with_augmented_labels(monkeypatch):
    """The close path must search with the same slopstopper-augmented labels
    that emit_issue used to create the issue — otherwise a post-PR-2 issue
    would never be closed."""
    monkeypatch.setattr(emit, "_gh_available", lambda: True)
    captured: dict = {}

    def fake_find(labels):
        captured["find_labels"] = list(labels)
        return None

    monkeypatch.setattr(emit, "_find_existing_issue", fake_find)
    emit._close_issue(["sast", "security"], "✅ now passing")
    assert captured["find_labels"] == ["slopstopper", "sast", "security"]


# ── public dispatcher ────────────────────────────────────────────


def test_emit_routes_pr_comment(monkeypatch):
    called: dict = {}

    def fake_pr(report_path, discrim):
        called["pr"] = (report_path, discrim)
        return 0

    monkeypatch.setattr(emit, "emit_pr_comment", fake_pr)
    rc = emit.emit("pr-comment", SAMPLE_META)
    assert rc == 0
    assert called["pr"][1] == "📚 Test Report"


def test_emit_routes_issue(monkeypatch):
    called: dict = {}

    def fake_issue(report_path, title, labels, followup, *, check_name=None):
        called["issue"] = (report_path, title, labels, followup, check_name)
        return 0

    monkeypatch.setattr(emit, "emit_issue", fake_issue)
    rc = emit.emit("issue", SAMPLE_META)
    assert rc == 0
    assert called["issue"][1] == "📚 Test Thresholds Exceeded"
    assert called["issue"][2] == ["test-label", "maintenance"]


def test_emit_rejects_unknown_target(capsys):
    rc = emit.emit("slack", SAMPLE_META)
    assert rc == 2
    assert "Unknown emit target" in capsys.readouterr().err


def test_emit_routes_on_pass_close_to_close_issue(monkeypatch):
    called: dict = {}

    def fake_close(labels, close_comment):
        called["close"] = (labels, close_comment)
        return 0

    monkeypatch.setattr(emit, "_close_issue", fake_close)
    rc = emit.emit("issue", SAMPLE_META, on_pass="close")
    assert rc == 0
    assert called["close"][0] == ["test-label", "maintenance"]
    # SAMPLE_META has no issue_close_comment → defaults to the module default.
    assert called["close"][1] == emit._DEFAULT_CLOSE_COMMENT


def test_emit_close_uses_meta_close_comment_when_present(monkeypatch):
    meta_with_close = {**SAMPLE_META, "issue_close_comment": "✅ custom-close"}
    called: dict = {}

    def fake_close(labels, close_comment):
        called["close"] = (labels, close_comment)
        return 0

    monkeypatch.setattr(emit, "_close_issue", fake_close)
    rc = emit.emit("issue", meta_with_close, on_pass="close")
    assert rc == 0
    assert called["close"][1] == "✅ custom-close"


def test_emit_without_on_pass_still_opens_issue(monkeypatch):
    """on_pass=None must not divert from the normal open-or-update path."""
    called: dict = {}

    def fake_issue(report_path, title, labels, followup, *, check_name=None):
        called["issue"] = True
        called["check_name"] = check_name
        return 0

    monkeypatch.setattr(emit, "emit_issue", fake_issue)
    rc = emit.emit("issue", SAMPLE_META)
    assert rc == 0
    assert called.get("issue") is True


def test_emit_threads_check_name_to_emit_issue(monkeypatch):
    called: dict = {}

    def fake_issue(report_path, title, labels, followup, *, check_name=None):
        called["check_name"] = check_name
        return 0

    monkeypatch.setattr(emit, "emit_issue", fake_issue)
    rc = emit.emit("issue", SAMPLE_META, check_name="hygiene:docs-size")
    assert rc == 0
    assert called["check_name"] == "hygiene:docs-size"
