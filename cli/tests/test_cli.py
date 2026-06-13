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


# ── config get subcommand ─────────────────────────────────────────


def test_config_get_prints_scalar(monkeypatch, capsys):
    monkeypatch.setattr(cli.config, "get", lambda key, default: "https://example.com")
    rc = cli.main(["config", "get", "urls.production"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "https://example.com"


def test_config_get_prints_list_comma_joined(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.config, "get", lambda key, default: ["ss-foo-check.yml", "ss-bar-check.yml"]
    )
    rc = cli.main(["config", "get", "workflows.disabled"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ss-foo-check.yml,ss-bar-check.yml"


def test_config_get_uses_default_when_missing(monkeypatch, capsys):
    # config.get returns whatever default was passed; emulate the
    # "missing" path by returning the default directly.
    monkeypatch.setattr(cli.config, "get", lambda key, default: default)
    rc = cli.main(["config", "get", "no.such.key", "fallback"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "fallback"


def test_config_get_prints_empty_when_none(monkeypatch, capsys):
    monkeypatch.setattr(cli.config, "get", lambda key, default: None)
    rc = cli.main(["config", "get", "headers.source"])
    assert rc == 0
    assert capsys.readouterr().out == "\n"


# ── templates subcommand ──────────────────────────────────────────


def test_templates_list_prints_each_with_status(isolated_cwd, capsys):
    rc = cli.main(["templates", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "playwright.config.js" in out
    assert "lighthouserc.json" in out
    assert "(bundled)" in out
    assert "(ejected" not in out


def test_templates_list_marks_ejected(isolated_cwd, capsys):
    override = isolated_cwd / ".ss" / "lighthouserc.json"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("{}")
    rc = cli.main(["templates", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    # The ejected entry carries the override marker; others remain bundled.
    assert "lighthouserc.json  (ejected" in out
    assert "playwright.config.js  (bundled)" in out


def test_templates_path_prints_resolved(isolated_cwd, capsys):
    rc = cli.main(["templates", "path", "lighthouserc.json"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith("lighthouserc.json")


def test_templates_path_unknown_returns_2(isolated_cwd, capsys):
    rc = cli.main(["templates", "path", "not-a-template"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown template" in err
    assert "known templates" in err


def test_templates_eject_creates_override(isolated_cwd, capsys):
    rc = cli.main(["templates", "eject", "lighthouserc.json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ejected" in out
    assert (isolated_cwd / ".ss" / "lighthouserc.json").exists()


def test_templates_eject_no_clobber(isolated_cwd, capsys):
    override = isolated_cwd / ".ss" / "lighthouserc.json"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("{ \"keep_me\": true }")
    rc = cli.main(["templates", "eject", "lighthouserc.json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "already exists" in out
    assert override.read_text() == "{ \"keep_me\": true }"


def test_templates_eject_unknown_returns_2(isolated_cwd, capsys):
    rc = cli.main(["templates", "eject", "not-a-template"])
    assert rc == 2
    assert "unknown template" in capsys.readouterr().err


# ── serve subcommand ──────────────────────────────────────────────


def test_serve_returns_1_when_node_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)
    rc = cli.main(["serve"])
    assert rc == 1
    assert "node is not available" in capsys.readouterr().err


def test_serve_execs_node_with_resolved_server_js(monkeypatch, isolated_cwd):
    captured: dict = {}

    def fake_execvp(file, args):
        captured["file"] = file
        captured["args"] = args
        # execvp doesn't return on success — to make the test path return,
        # we just don't raise. _dispatch_serve will fall through to its
        # "unreachable" return 1.

    monkeypatch.setattr(cli.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(cli.os, "execvp", fake_execvp)

    cli.main(["serve"])
    assert captured["file"] == "node"
    assert captured["args"][0] == "node"
    # Should resolve to the bundled server.js (no .ss/ override in the
    # isolated cwd).
    assert captured["args"][1].endswith("server.js")


def test_serve_prefers_ss_override(monkeypatch, isolated_cwd):
    override = isolated_cwd / ".ss" / "server.js"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("// custom")

    captured: dict = {}

    def fake_execvp(file, args):
        captured["args"] = args

    monkeypatch.setattr(cli.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(cli.os, "execvp", fake_execvp)

    cli.main(["serve"])
    # Resolved path should be the override, not the bundled file.
    from pathlib import Path
    assert Path(captured["args"][1]) == Path(".ss/server.js")


def test_config_get_default_default_is_empty_string(monkeypatch, capsys):
    """Matches the bash load_config.py shim: missing key + no default = ''"""
    captured = {}
    monkeypatch.setattr(
        cli.config,
        "get",
        lambda key, default: captured.update({"default": default}) or default,
    )
    rc = cli.main(["config", "get", "no.such.key"])
    assert rc == 0
    assert captured["default"] == ""
    assert capsys.readouterr().out == "\n"
