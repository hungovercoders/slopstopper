"""Tests for the CLI dispatcher (cli.py)."""

from __future__ import annotations

import pytest

from slopstopper import cli


def test_version_flag_prints_and_exits(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "slopstopper" in out


def test_run_unknown_check_returns_2(capsys):
    rc = cli.main(["run", "no-such:check"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown check" in err
    assert "known checks" in err


def test_no_command_errors(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code != 0


# ── emit subcommand ──────────────────────────────────────────────


def test_emit_unknown_check_returns_2(capsys):
    rc = cli.main(["emit", "no-such:check", "--target", "pr-comment"])
    assert rc == 2
    assert "unknown check" in capsys.readouterr().err


def test_emit_no_meta_returns_2(monkeypatch, capsys):
    # Pick a check that has no META yet — accessibility currently doesn't.
    rc = cli.main(["emit", "reliability:accessibility", "--target", "pr-comment"])
    assert rc == 2
    assert "has no META" in capsys.readouterr().err


def test_emit_routes_to_emit_module(monkeypatch):
    """When the check has META, the dispatcher hands off to emit.emit
    with the target and the META dict."""
    called: dict = {}

    def fake_emit(target, meta):
        called["target"] = target
        called["meta"] = meta
        return 0

    monkeypatch.setattr(cli.emit_mod, "emit", fake_emit)
    rc = cli.main(["emit", "hygiene:docs-size", "--target", "issue"])
    assert rc == 0
    assert called["target"] == "issue"
    assert "comment_discriminator" in called["meta"]


def test_emit_requires_target_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["emit", "hygiene:docs-size"])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "required" in err or "--target" in err


# ── discover subcommand ───────────────────────────────────────────


def test_discover_prints_comma_joined_paths(monkeypatch, capsys):
    captured = {}

    def fake_discover(check, event):
        captured["check"] = check
        captured["event"] = event
        return ["/", "/blog", "/about"]

    monkeypatch.setattr(cli.discovery, "discover", fake_discover)
    rc = cli.main(["discover", "smoke", "--event", "pr"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "/,/blog,/about"
    assert captured == {"check": "smoke", "event": "pr"}


def test_discover_returns_2_when_no_paths(monkeypatch, capsys):
    monkeypatch.setattr(cli.discovery, "discover", lambda check, event: [])
    rc = cli.main(["discover", "broken_links", "--event", "main"])
    assert rc == 2
    assert capsys.readouterr().out == ""


def test_discover_accepts_hyphen_alias_for_broken_links(monkeypatch):
    """`broken-links` (hyphen, slopstopper-style) maps to the same
    underscore-form `broken_links` the discovery module expects."""
    captured = {}

    def fake_discover(check, event):
        captured["check"] = check
        return ["/"]

    monkeypatch.setattr(cli.discovery, "discover", fake_discover)
    rc = cli.main(["discover", "broken-links", "--event", "local"])
    assert rc == 0
    assert captured["check"] == "broken_links"


def test_discover_returns_1_on_internal_error(monkeypatch, capsys):
    def boom(check, event):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(cli.discovery, "discover", boom)
    rc = cli.main(["discover", "seo", "--event", "cron"])
    assert rc == 1
    assert "kaboom" in capsys.readouterr().err


def test_discover_rejects_unknown_check(capsys):
    with pytest.raises(SystemExit):
        cli.main(["discover", "nope", "--event", "local"])


def test_discover_default_event_is_local(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        cli.discovery,
        "discover",
        lambda check, event: captured.update({"event": event}) or ["/"],
    )
    rc = cli.main(["discover", "smoke"])
    assert rc == 0
    assert captured["event"] == "local"
