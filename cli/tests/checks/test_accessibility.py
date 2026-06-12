"""Tests for the reliability:accessibility check (Playwright + axe-core wrapper)."""

from __future__ import annotations

import os
import subprocess

from slopstopper.checks import accessibility


# ── helpers ──────────────────────────────────────────────────────


def test_parse_args_defaults():
    parsed = accessibility._parse_args(None)
    assert parsed.url is None
    assert parsed.ci is False


def test_parse_args_explicit():
    parsed = accessibility._parse_args(["--url", "https://example.com", "--ci"])
    assert parsed.url == "https://example.com"
    assert parsed.ci is True


def test_resolve_url_prefers_flag(monkeypatch):
    monkeypatch.setenv("ACCESSIBILITY_TEST_URL", "https://from-a11y")
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-smoke")
    assert accessibility._resolve_url("https://from-flag") == "https://from-flag"


def test_resolve_url_falls_through_a11y_env(monkeypatch):
    monkeypatch.setenv("ACCESSIBILITY_TEST_URL", "https://from-a11y")
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-smoke")
    assert accessibility._resolve_url(None) == "https://from-a11y"


def test_resolve_url_falls_through_smoke_env(monkeypatch):
    monkeypatch.delenv("ACCESSIBILITY_TEST_URL", raising=False)
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-smoke")
    assert accessibility._resolve_url(None) == "https://from-smoke"


def test_resolve_url_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("ACCESSIBILITY_TEST_URL", raising=False)
    monkeypatch.delenv("SMOKE_TEST_URL", raising=False)
    assert accessibility._resolve_url(None) is None


def test_discover_pages_defaults_to_root_when_unconfigured(isolated_cwd):
    # No .slopstopper.yml, no env vars — discovery falls through to "/"
    assert accessibility._discover_pages() == "/"


def test_discover_pages_returns_joined_paths(monkeypatch, isolated_cwd):
    monkeypatch.setattr(accessibility.discovery, "discover", lambda check, event: ["/", "/blog"])
    assert accessibility._discover_pages() == "/,/blog"


def test_discover_pages_returns_none_on_discovery_failure(monkeypatch, isolated_cwd):
    def boom(check, event):
        raise RuntimeError("boom")

    monkeypatch.setattr(accessibility.discovery, "discover", boom)
    assert accessibility._discover_pages() is None


def test_build_env_threads_url(isolated_cwd, monkeypatch):
    monkeypatch.delenv("ACCESSIBILITY_PAGES", raising=False)
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: None)
    env = accessibility._build_env("https://example.com", ci_mode=False)
    assert env["ACCESSIBILITY_TEST_URL"] == "https://example.com"


def test_build_env_calls_discover_pages_when_unset(isolated_cwd, monkeypatch):
    monkeypatch.delenv("ACCESSIBILITY_PAGES", raising=False)
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: "/,/about")
    env = accessibility._build_env("https://example.com", ci_mode=False)
    assert env["ACCESSIBILITY_PAGES"] == "/,/about"


def test_build_env_preserves_caller_pages(monkeypatch):
    monkeypatch.setenv("ACCESSIBILITY_PAGES", "/preset")
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: "/should-not-use")
    env = accessibility._build_env("https://example.com", ci_mode=False)
    assert env["ACCESSIBILITY_PAGES"] == "/preset"


def test_build_env_does_not_set_ci_when_default(isolated_cwd, monkeypatch):
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: None)
    caller_ci = os.environ.get("CI")
    env = accessibility._build_env("https://example.com", ci_mode=False)
    assert env.get("CI") == caller_ci


def test_build_env_sets_ci_when_ci_mode(isolated_cwd, monkeypatch):
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: None)
    env = accessibility._build_env("https://example.com", ci_mode=True)
    assert env["CI"] == "true"


def test_build_cmd_default_reporter():
    cmd = accessibility._build_cmd(ci_mode=False)
    assert cmd[0] == "npx"
    assert "playwright" in cmd
    assert "--reporter=list" in cmd
    assert str(accessibility.SPEC_PATH) in cmd


def test_build_cmd_ci_uses_list_html_reporter():
    cmd = accessibility._build_cmd(ci_mode=True)
    assert "--reporter=list,html" in cmd


# ── subprocess / runtime ─────────────────────────────────────────


def test_npx_available_via_which(monkeypatch):
    monkeypatch.setattr(accessibility.shutil, "which", lambda _: "/usr/bin/npx")
    assert accessibility._npx_available() is True
    monkeypatch.setattr(accessibility.shutil, "which", lambda _: None)
    assert accessibility._npx_available() is False


def test_run_returns_one_when_npx_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(accessibility, "_npx_available", lambda: False)
    rc = accessibility.run()
    assert rc == 1
    assert "npx is not available" in capsys.readouterr().out


def test_run_returns_one_when_url_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(accessibility, "_npx_available", lambda: True)
    monkeypatch.delenv("ACCESSIBILITY_TEST_URL", raising=False)
    monkeypatch.delenv("SMOKE_TEST_URL", raising=False)
    rc = accessibility.run([])
    assert rc == 1
    assert "accessibility target URL is required" in capsys.readouterr().out


def test_run_returns_one_when_spec_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(accessibility, "_npx_available", lambda: True)
    rc = accessibility.run(["--url", "https://example.com"])
    assert rc == 1
    assert "Accessibility spec not found" in capsys.readouterr().out


def test_run_invokes_playwright(monkeypatch, isolated_cwd):
    accessibility.SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    accessibility.SPEC_PATH.write_text("// fake spec")

    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(accessibility, "_npx_available", lambda: True)
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: None)
    monkeypatch.setattr(accessibility.subprocess, "run", fake_run)

    rc = accessibility.run(["--url", "https://example.com"])
    assert rc == 0
    assert captured["cmd"][:2] == ["npx", "playwright"]
    assert "--reporter=list" in captured["cmd"]
    assert captured["env"]["ACCESSIBILITY_TEST_URL"] == "https://example.com"


def test_run_ci_mode_threads_html_reporter(monkeypatch, isolated_cwd):
    accessibility.SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    accessibility.SPEC_PATH.write_text("// fake spec")

    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(accessibility, "_npx_available", lambda: True)
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: None)
    monkeypatch.setattr(accessibility.subprocess, "run", fake_run)

    rc = accessibility.run(["--url", "https://example.com", "--ci"])
    assert rc == 0
    assert "--reporter=list,html" in captured["cmd"]
    assert captured["env"]["CI"] == "true"


def test_run_propagates_playwright_failure(monkeypatch, isolated_cwd):
    accessibility.SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    accessibility.SPEC_PATH.write_text("// fake spec")

    monkeypatch.setattr(accessibility, "_npx_available", lambda: True)
    monkeypatch.setattr(accessibility, "_discover_pages", lambda: None)
    monkeypatch.setattr(
        accessibility.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 1),
    )

    rc = accessibility.run(["--url", "https://example.com"])
    assert rc == 1
