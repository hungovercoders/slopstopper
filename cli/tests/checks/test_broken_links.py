"""Tests for the reliability:broken-links check (Playwright wrapper)."""

from __future__ import annotations

import os
import subprocess

from slopstopper.checks import broken_links


def test_parse_args_defaults():
    parsed = broken_links._parse_args(None)
    assert parsed.url is None
    assert parsed.ci is False


def test_parse_args_explicit():
    parsed = broken_links._parse_args(["--url", "https://example.com", "--ci"])
    assert parsed.url == "https://example.com"
    assert parsed.ci is True


def test_resolve_url_prefers_flag(monkeypatch):
    monkeypatch.setenv("BROKEN_LINKS_TEST_URL", "https://from-bl")
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-smoke")
    assert broken_links._resolve_url("https://from-flag") == "https://from-flag"


def test_resolve_url_falls_through_bl_env(monkeypatch):
    monkeypatch.setenv("BROKEN_LINKS_TEST_URL", "https://from-bl")
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-smoke")
    assert broken_links._resolve_url(None) == "https://from-bl"


def test_resolve_url_falls_through_smoke_env(monkeypatch):
    monkeypatch.delenv("BROKEN_LINKS_TEST_URL", raising=False)
    monkeypatch.setenv("SMOKE_TEST_URL", "https://from-smoke")
    assert broken_links._resolve_url(None) == "https://from-smoke"


def test_resolve_url_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("BROKEN_LINKS_TEST_URL", raising=False)
    monkeypatch.delenv("SMOKE_TEST_URL", raising=False)
    assert broken_links._resolve_url(None) is None


def test_discover_pages_defaults_to_root_when_unconfigured(isolated_cwd):
    assert broken_links._discover_pages() == "/"


def test_discover_pages_returns_joined_paths(monkeypatch, isolated_cwd):
    monkeypatch.setattr(broken_links.discovery, "discover", lambda check, event: ["/", "/blog"])
    assert broken_links._discover_pages() == "/,/blog"


def test_discover_pages_returns_none_on_discovery_failure(monkeypatch, isolated_cwd):
    def boom(check, event):
        raise RuntimeError("boom")

    monkeypatch.setattr(broken_links.discovery, "discover", boom)
    assert broken_links._discover_pages() is None


def test_build_env_threads_url(isolated_cwd, monkeypatch):
    monkeypatch.delenv("BROKEN_LINKS_PAGES", raising=False)
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    env = broken_links._build_env("https://example.com", ci_mode=False)
    assert env["BROKEN_LINKS_TEST_URL"] == "https://example.com"


def test_build_env_calls_discover_pages_when_unset(isolated_cwd, monkeypatch):
    monkeypatch.delenv("BROKEN_LINKS_PAGES", raising=False)
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: "/,/about")
    env = broken_links._build_env("https://example.com", ci_mode=False)
    assert env["BROKEN_LINKS_PAGES"] == "/,/about"


def test_build_env_preserves_caller_pages(monkeypatch):
    monkeypatch.setenv("BROKEN_LINKS_PAGES", "/preset")
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: "/should-not-use")
    env = broken_links._build_env("https://example.com", ci_mode=False)
    assert env["BROKEN_LINKS_PAGES"] == "/preset"


def test_build_env_does_not_set_ci_when_default(isolated_cwd, monkeypatch):
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    caller_ci = os.environ.get("CI")
    env = broken_links._build_env("https://example.com", ci_mode=False)
    assert env.get("CI") == caller_ci


def test_build_env_sets_ci_when_ci_mode(isolated_cwd, monkeypatch):
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    env = broken_links._build_env("https://example.com", ci_mode=True)
    assert env["CI"] == "true"


def test_build_cmd_default_reporter():
    cmd = broken_links._build_cmd(ci_mode=False)
    assert cmd[0] == "npx"
    assert "playwright" in cmd
    assert "--reporter=list" in cmd
    assert any("broken-links.spec.ts" in arg for arg in cmd)


def test_build_cmd_ci_uses_list_html_reporter():
    cmd = broken_links._build_cmd(ci_mode=True)
    assert "--reporter=list,html" in cmd


def test_npx_available_via_which(monkeypatch):
    monkeypatch.setattr(broken_links.shutil, "which", lambda _: "/usr/bin/npx")
    assert broken_links._npx_available() is True
    monkeypatch.setattr(broken_links.shutil, "which", lambda _: None)
    assert broken_links._npx_available() is False


def test_run_returns_one_when_npx_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(broken_links, "_npx_available", lambda: False)
    rc = broken_links.run()
    assert rc == 1
    assert "npx is not available" in capsys.readouterr().out


def test_run_returns_one_when_url_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(broken_links, "_npx_available", lambda: True)
    monkeypatch.delenv("BROKEN_LINKS_TEST_URL", raising=False)
    monkeypatch.delenv("SMOKE_TEST_URL", raising=False)
    rc = broken_links.run([])
    assert rc == 1
    assert "broken-links target URL is required" in capsys.readouterr().out


def test_run_invokes_playwright(monkeypatch, isolated_cwd):
    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(broken_links, "_npx_available", lambda: True)
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    monkeypatch.setattr(broken_links.subprocess, "run", fake_run)

    rc = broken_links.run(["--url", "https://example.com"])
    assert rc == 0
    assert captured["cmd"][:2] == ["npx", "playwright"]
    assert "--reporter=list" in captured["cmd"]
    assert captured["env"]["BROKEN_LINKS_TEST_URL"] == "https://example.com"


def test_run_ci_mode_threads_html_reporter(monkeypatch, isolated_cwd):
    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(broken_links, "_npx_available", lambda: True)
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    monkeypatch.setattr(broken_links.subprocess, "run", fake_run)

    rc = broken_links.run(["--url", "https://example.com", "--ci"])
    assert rc == 0
    assert "--reporter=list,html" in captured["cmd"]
    assert captured["env"]["CI"] == "true"


def test_run_propagates_playwright_failure(monkeypatch, isolated_cwd):
    monkeypatch.setattr(broken_links, "_npx_available", lambda: True)
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    monkeypatch.setattr(
        broken_links.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 1),
    )

    rc = broken_links.run(["--url", "https://example.com"])
    assert rc == 1


# ── report writing ────────────────────────────────────────────────


def test_run_writes_report_on_pass(monkeypatch, isolated_cwd):
    monkeypatch.setattr(broken_links, "_npx_available", lambda: True)
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    monkeypatch.setattr(
        broken_links.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 0),
    )
    rc = broken_links.run(["--url", "https://example.com"])
    assert rc == 0
    body = broken_links.REPORT_MD.read_text()
    assert "PASSED" in body
    assert "https://example.com" in body


def test_run_writes_report_on_failure(monkeypatch, isolated_cwd):
    monkeypatch.setattr(broken_links, "_npx_available", lambda: True)
    monkeypatch.setattr(broken_links, "_discover_pages", lambda: None)
    monkeypatch.setattr(
        broken_links.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 1),
    )
    rc = broken_links.run(["--url", "https://example.com"])
    assert rc == 1
    body = broken_links.REPORT_MD.read_text()
    assert "FAILED" in body
    assert "playwright-report" in body


def test_meta_includes_reliability_and_broken_links_labels():
    assert "broken-links" in broken_links.META["issue_labels"]
    assert "reliability" in broken_links.META["issue_labels"]
