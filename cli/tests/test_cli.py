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


def test_bare_invocation_prints_banner_and_exits_zero(capsys):
    """No args → friendly banner + exit 0 (not an error)."""
    rc = cli.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "slopstopper" in out
    assert "Commands:" in out
    assert "Quick start:" in out
    assert "run" in out
    assert "doctor" in out


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
    with the target, META dict, check_name, and on_pass kwargs."""
    called: dict = {}

    def fake_emit(target, meta, *, check_name=None, on_pass=None):
        called["target"] = target
        called["meta"] = meta
        called["check_name"] = check_name
        called["on_pass"] = on_pass
        return 0

    monkeypatch.setattr(cli.emit_mod, "emit", fake_emit)
    rc = cli.main(["emit", "hygiene:docs-size", "--target", "issue"])
    assert rc == 0
    assert called["target"] == "issue"
    assert called["check_name"] == "hygiene:docs-size"
    assert called["on_pass"] is None
    assert "comment_discriminator" in called["meta"]


def test_emit_threads_on_pass_close_through(monkeypatch):
    called: dict = {}

    def fake_emit(target, meta, *, check_name=None, on_pass=None):
        called["on_pass"] = on_pass
        return 0

    monkeypatch.setattr(cli.emit_mod, "emit", fake_emit)
    rc = cli.main(["emit", "hygiene:docs-size", "--target", "issue", "--on-pass=close"])
    assert rc == 0
    assert called["on_pass"] == "close"


def test_emit_rejects_on_pass_with_pr_comment_target(capsys):
    rc = cli.main(["emit", "hygiene:docs-size", "--target", "pr-comment", "--on-pass=close"])
    assert rc == 2
    assert "--on-pass is only valid with --target issue" in capsys.readouterr().err


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


# ── checks list subcommand ────────────────────────────────────────


def test_checks_list_prints_every_registered_check(isolated_cwd, capsys):
    rc = cli.main(["checks", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    # Spot-check a few known names from REGISTRY.
    assert "hygiene:docs-size" in out
    assert "security:secrets" in out
    assert "reliability:cwv" in out


def test_checks_list_filters_by_category(isolated_cwd, capsys):
    rc = cli.main(["checks", "list", "--category", "security"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "security:secrets" in out
    # Hygiene checks shouldn't appear under --category=security.
    assert "hygiene:docs-size" not in out


def test_checks_list_json_emits_machine_readable(isolated_cwd, capsys):
    import json
    rc = cli.main(["checks", "list", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    names = {e["name"] for e in data}
    assert "hygiene:docs-size" in names
    assert all("summary" in e for e in data)


def test_checks_list_empty_category_says_so(isolated_cwd, capsys, monkeypatch):
    # Force the filtered list to be empty by patching the registry view.
    monkeypatch.setattr(cli, "REGISTRY", {})
    rc = cli.main(["checks", "list", "--category", "security"])
    assert rc == 0
    assert "No checks registered" in capsys.readouterr().out


# ── doctor subcommand ─────────────────────────────────────────────


def test_doctor_passes_when_all_tools_present(isolated_cwd, capsys, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda _: "/usr/bin/stub")
    monkeypatch.setattr(cli, "_tool_version", lambda _: "stub 1.0")
    rc = cli.main(["doctor"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "All required tools available" in out
    # Each tool from _DOCTOR_TOOLS should be listed.
    for tool, _, _ in cli._DOCTOR_TOOLS:
        assert tool in out


def test_doctor_fails_when_required_tool_missing(isolated_cwd, capsys, monkeypatch):
    """Missing trivy with security:vulnerability:all enabled → exit 1."""
    monkeypatch.setattr(cli.shutil, "which", lambda tool: None if tool == "trivy" else "/x")
    monkeypatch.setattr(cli, "_tool_version", lambda _: "")
    monkeypatch.setattr(cli, "_disabled_workflows", lambda: set())
    rc = cli.main(["doctor"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "trivy" in out
    assert "not installed" in out
    assert "required tool(s) missing" in out


def test_doctor_skips_disabled_check_tools(isolated_cwd, capsys, monkeypatch):
    """Missing semgrep is fine if security:sast is in workflows.disabled."""
    monkeypatch.setattr(
        cli.shutil, "which", lambda tool: None if tool == "semgrep" else "/x"
    )
    monkeypatch.setattr(cli, "_tool_version", lambda _: "")
    monkeypatch.setattr(
        cli, "_disabled_workflows", lambda: {"ss-security-sast-check.yml"}
    )
    rc = cli.main(["doctor"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "disabled in .slopstopper.yml" in out


def test_doctor_fails_when_node_or_gh_missing(isolated_cwd, capsys, monkeypatch):
    """node and gh are needed by the CLI itself (no disabled-bypass)."""
    monkeypatch.setattr(cli.shutil, "which", lambda tool: None if tool == "node" else "/x")
    monkeypatch.setattr(cli, "_tool_version", lambda _: "")
    rc = cli.main(["doctor"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "node" in out
    assert "the CLI itself" in out


# ── --quiet global flag ───────────────────────────────────────────


def test_quiet_flag_suppresses_check_output(isolated_cwd, capsys, monkeypatch):
    """--quiet flips output.QUIET so check decorations vanish."""
    from slopstopper import output as out_mod

    seen = {}

    def fake_run(_args):
        out_mod.running("would be hidden")
        out_mod.success("would be hidden")
        seen["quiet"] = out_mod.QUIET
        return 0

    monkeypatch.setitem(cli.REGISTRY, "hygiene:test-fake", fake_run)
    rc = cli.main(["--quiet", "run", "hygiene:test-fake"])
    assert rc == 0
    assert seen["quiet"] is True
    # No "would be hidden" lines on stdout.
    assert "would be hidden" not in capsys.readouterr().out


def test_quiet_flag_does_not_suppress_errors(isolated_cwd, capsys, monkeypatch):
    """--quiet still lets errors through (they're load-bearing)."""
    from slopstopper import output as out_mod

    def fake_run(_args):
        out_mod.error("critical error must show")
        return 1

    monkeypatch.setitem(cli.REGISTRY, "hygiene:test-fake-err", fake_run)
    rc = cli.main(["--quiet", "run", "hygiene:test-fake-err"])
    assert rc == 1
    assert "critical error must show" in capsys.readouterr().out


def test_quiet_default_is_off(isolated_cwd, capsys, monkeypatch):
    """Without --quiet, the QUIET flag stays False."""
    from slopstopper import output as out_mod

    seen = {}

    def fake_run(_args):
        seen["quiet"] = out_mod.QUIET
        return 0

    monkeypatch.setitem(cli.REGISTRY, "hygiene:test-fake-default", fake_run)
    cli.main(["run", "hygiene:test-fake-default"])
    assert seen["quiet"] is False
