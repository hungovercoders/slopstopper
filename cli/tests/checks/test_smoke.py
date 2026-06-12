"""Tests for the reliability:smoke check (Playwright wrapper)."""

from __future__ import annotations

import os
import subprocess

from slopstopper.checks import smoke


# ── helpers ──────────────────────────────────────────────────────


def test_parse_args_defaults():
    parsed = smoke._parse_args(None)
    assert parsed.url is None
    assert parsed.ci is False


def test_parse_args_explicit_url_and_ci():
    parsed = smoke._parse_args(["--url", "https://example.com", "--ci"])
    assert parsed.url == "https://example.com"
    assert parsed.ci is True


def test_resolve_url_prefers_flag(monkeypatch):
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-env")
    assert smoke._resolve_url("https://from-flag") == "https://from-flag"


def test_resolve_url_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-env")
    assert smoke._resolve_url(None) == "https://from-env"


def test_resolve_url_returns_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("SMOKE_TEST_URL", raising=False)
    assert smoke._resolve_url(None) is None


def test_build_env_threads_url_and_config_defaults(isolated_cwd, monkeypatch):
    monkeypatch.delenv("SMOKE_OG_IMAGE_PATH", raising=False)
    monkeypatch.delenv("SMOKE_PAGES", raising=False)
    # GitHub Actions sets CI=true in the runner env. We're asserting that
    # _build_env doesn't ADD CI when ci_mode=False, not that CI is absent
    # from the caller's environment. Snapshot caller-CI before the call.
    caller_ci = os.environ.get("CI")
    env = smoke._build_env("https://example.com", ci_mode=False)
    assert env["SMOKE_TEST_URL"] == "https://example.com"
    assert env["SMOKE_OG_IMAGE_PATH"] == "/og-image.png"
    assert env["SMOKE_PAGES"] == "/"
    # ci_mode=False must not touch CI either direction
    assert env.get("CI") == caller_ci


def test_build_env_reads_config_keys(write_config, monkeypatch):
    monkeypatch.delenv("SMOKE_OG_IMAGE_PATH", raising=False)
    monkeypatch.delenv("SMOKE_PAGES", raising=False)
    write_config(
        "smoke:\n  og_image_path: /static/og.png\npages:\n  smoke: /,/blog,/about\n"
    )
    env = smoke._build_env("https://example.com", ci_mode=False)
    assert env["SMOKE_OG_IMAGE_PATH"] == "/static/og.png"
    assert env["SMOKE_PAGES"] == "/,/blog,/about"


def test_build_env_respects_caller_env_vars(monkeypatch):
    monkeypatch.setenv("SMOKE_OG_IMAGE_PATH", "/preset.png")
    monkeypatch.setenv("SMOKE_PAGES", "/preset-page")
    env = smoke._build_env("https://example.com", ci_mode=False)
    # setdefault means caller's env wins over config defaults
    assert env["SMOKE_OG_IMAGE_PATH"] == "/preset.png"
    assert env["SMOKE_PAGES"] == "/preset-page"


def test_build_env_sets_ci_when_ci_mode():
    env = smoke._build_env("https://example.com", ci_mode=True)
    assert env["CI"] == "true"


def test_build_cmd_default_reporter():
    cmd = smoke._build_cmd(ci_mode=False)
    assert cmd[0] == "npx"
    assert "playwright" in cmd
    assert "test" in cmd
    assert "--reporter=list" in cmd
    assert str(smoke.SPEC_PATH) in cmd


def test_build_cmd_ci_uses_list_html_reporter():
    cmd = smoke._build_cmd(ci_mode=True)
    assert "--reporter=list,html" in cmd


# ── subprocess / runtime ─────────────────────────────────────────


def test_npx_available_via_which(monkeypatch):
    monkeypatch.setattr(smoke.shutil, "which", lambda _: "/usr/bin/npx")
    assert smoke._npx_available() is True
    monkeypatch.setattr(smoke.shutil, "which", lambda _: None)
    assert smoke._npx_available() is False


def test_run_returns_one_when_npx_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(smoke, "_npx_available", lambda: False)
    rc = smoke.run()
    assert rc == 1
    assert "npx is not available" in capsys.readouterr().out


def test_run_returns_one_when_url_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(smoke, "_npx_available", lambda: True)
    monkeypatch.delenv("SMOKE_TEST_URL", raising=False)
    rc = smoke.run([])
    assert rc == 1
    out = capsys.readouterr().out
    assert "smoke target URL is required" in out


def test_run_returns_one_when_spec_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(smoke, "_npx_available", lambda: True)
    rc = smoke.run(["--url", "https://example.com"])
    assert rc == 1
    assert "Smoke spec not found" in capsys.readouterr().out


def test_run_invokes_playwright_with_expected_args(monkeypatch, isolated_cwd):
    smoke.SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    smoke.SPEC_PATH.write_text("// fake spec")

    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(smoke, "_npx_available", lambda: True)
    monkeypatch.setattr(smoke.subprocess, "run", fake_run)

    rc = smoke.run(["--url", "https://example.com"])
    assert rc == 0
    assert captured["cmd"][:2] == ["npx", "playwright"]
    assert "--reporter=list" in captured["cmd"]
    assert captured["env"]["SMOKE_TEST_URL"] == "https://example.com"


def test_run_ci_mode_threads_html_reporter_and_ci_env(monkeypatch, isolated_cwd):
    smoke.SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    smoke.SPEC_PATH.write_text("// fake spec")

    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(smoke, "_npx_available", lambda: True)
    monkeypatch.setattr(smoke.subprocess, "run", fake_run)

    rc = smoke.run(["--url", "https://example.com", "--ci"])
    assert rc == 0
    assert "--reporter=list,html" in captured["cmd"]
    assert captured["env"]["CI"] == "true"


def test_run_propagates_playwright_failure(monkeypatch, isolated_cwd):
    smoke.SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    smoke.SPEC_PATH.write_text("// fake spec")

    monkeypatch.setattr(smoke, "_npx_available", lambda: True)
    monkeypatch.setattr(
        smoke.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 1),
    )

    rc = smoke.run(["--url", "https://example.com"])
    assert rc == 1
