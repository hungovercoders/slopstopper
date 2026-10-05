"""Tests for the reliability:e2e check (Playwright wrapper)."""

from __future__ import annotations

import os
import subprocess

from slopstopper.checks import _tools, e2e
from tests._fakes import playwright_failed


# ── helpers ──────────────────────────────────────────────────────


def test_parse_args_defaults():
    parsed = e2e._parse_args(None)
    assert parsed.url is None
    assert parsed.ci is False


def test_parse_args_explicit_url_and_ci():
    parsed = e2e._parse_args(["--url", "https://example.com", "--ci"])
    assert parsed.url == "https://example.com"
    assert parsed.ci is True


def test_parse_args_positional_url():
    parsed = e2e._parse_args(["http://localhost:8080"])
    assert parsed.url_positional == "http://localhost:8080"


def test_resolve_url_prefers_flag(monkeypatch):
    monkeypatch.setenv("E2E_TEST_URL", "https://from-env")
    assert e2e._resolve_url("https://from-flag") == "https://from-flag"


def test_resolve_url_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("E2E_TEST_URL", "https://from-env")
    assert e2e._resolve_url(None) == "https://from-env"


def test_resolve_url_returns_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("E2E_TEST_URL", raising=False)
    assert e2e._resolve_url(None) is None


def test_build_env_threads_url_and_config_defaults(isolated_cwd, monkeypatch):
    monkeypatch.delenv("E2E_PAGES", raising=False)
    monkeypatch.delenv("E2E_MAX_LINKS", raising=False)
    caller_ci = os.environ.get("CI")
    env = e2e._build_env("https://example.com", ci_mode=False)
    assert env["E2E_TEST_URL"] == "https://example.com"
    assert env["E2E_PAGES"] == "/"
    assert env["E2E_MAX_LINKS"] == "25"
    assert env.get("CI") == caller_ci


def test_build_env_reads_config_keys(write_config, monkeypatch):
    monkeypatch.delenv("E2E_PAGES", raising=False)
    monkeypatch.delenv("E2E_MAX_LINKS", raising=False)
    write_config("pages:\n  e2e: /,/pricing\ne2e:\n  max_links: 5\n")
    env = e2e._build_env("https://example.com", ci_mode=False)
    assert env["E2E_PAGES"] == "/,/pricing"
    assert env["E2E_MAX_LINKS"] == "5"


def test_build_env_falls_back_when_max_links_is_not_a_positive_int(write_config, monkeypatch, capsys):
    monkeypatch.delenv("E2E_MAX_LINKS", raising=False)
    for raw in ("e2e:\n  max_links: all\n", "e2e:\n  max_links:\n", "e2e:\n  max_links: 0\n"):
        write_config(raw)
        env = e2e._build_env("https://example.com", ci_mode=False)
        assert env["E2E_MAX_LINKS"] == "25", raw
    assert "not a positive integer" in capsys.readouterr().out


def test_build_env_respects_caller_env_vars(monkeypatch):
    monkeypatch.setenv("E2E_PAGES", "/preset")
    monkeypatch.setenv("E2E_MAX_LINKS", "3")
    env = e2e._build_env("https://example.com", ci_mode=False)
    assert env["E2E_PAGES"] == "/preset"
    assert env["E2E_MAX_LINKS"] == "3"


def test_build_env_sets_ci_when_ci_mode():
    env = e2e._build_env("https://example.com", ci_mode=True)
    assert env["CI"] == "true"


def test_build_cmd_default_reporter():
    cmd = e2e._build_cmd(ci_mode=False)
    assert cmd[0] == "npx"
    assert "playwright" in cmd
    assert "--reporter=list,json" in cmd
    assert any("e2e.spec.ts" in arg for arg in cmd)


def test_build_cmd_ci_uses_list_html_reporter():
    cmd = e2e._build_cmd(ci_mode=True)
    assert "--reporter=list,html,json" in cmd


# ── subprocess / runtime ─────────────────────────────────────────


def test_npx_available_via_which(monkeypatch):
    monkeypatch.setattr(_tools.shutil, "which", lambda _: "/usr/bin/npx")
    assert e2e._npx_available() is True
    monkeypatch.setattr(_tools.shutil, "which", lambda _: None)
    assert e2e._npx_available() is False


def test_run_returns_two_when_npx_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(e2e, "_npx_available", lambda: False)
    assert e2e.run() == 2
    assert "npx is not available" in capsys.readouterr().out


def test_run_returns_two_when_url_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(e2e, "_npx_available", lambda: True)
    monkeypatch.delenv("E2E_TEST_URL", raising=False)
    assert e2e.run([]) == 2
    assert "e2e target URL is required" in capsys.readouterr().out


def test_run_invokes_playwright_with_expected_args(monkeypatch, isolated_cwd):
    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(e2e, "_npx_available", lambda: True)
    monkeypatch.setattr(e2e.subprocess, "run", fake_run)

    assert e2e.run(["--url", "https://example.com"]) == 0
    assert captured["cmd"][:2] == ["npx", "playwright"]
    assert "--reporter=list,json" in captured["cmd"]
    assert captured["env"]["E2E_TEST_URL"] == "https://example.com"


def test_run_ci_mode_threads_html_reporter_and_ci_env(monkeypatch, isolated_cwd):
    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(e2e, "_npx_available", lambda: True)
    monkeypatch.setattr(e2e.subprocess, "run", fake_run)

    assert e2e.run(["https://example.com", "--ci"]) == 0
    assert "--reporter=list,html,json" in captured["cmd"]
    assert captured["env"]["CI"] == "true"


def test_run_propagates_playwright_failure(monkeypatch, isolated_cwd):
    monkeypatch.setattr(e2e, "_npx_available", lambda: True)
    monkeypatch.setattr(e2e.subprocess, "run", playwright_failed)
    assert e2e.run(["--url", "https://example.com"]) == 1


def test_run_returns_two_when_playwright_never_ran(monkeypatch, isolated_cwd):
    """Exit 1 with no JSON report means the suite did not reach a verdict."""
    monkeypatch.setattr(e2e, "_npx_available", lambda: True)
    monkeypatch.setattr(
        e2e.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 1),
    )
    assert e2e.run(["--url", "https://example.com"]) == 2


# ── report writing ────────────────────────────────────────────────


def test_run_writes_report_on_pass(monkeypatch, isolated_cwd):
    monkeypatch.setattr(e2e, "_npx_available", lambda: True)
    monkeypatch.setattr(
        e2e.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 0),
    )
    assert e2e.run(["--url", "https://example.com"]) == 0
    body = e2e.REPORT_MD.read_text()
    assert "PASSED" in body
    assert "https://example.com" in body


def test_run_writes_report_on_failure_with_playwright_link(monkeypatch, isolated_cwd):
    monkeypatch.setattr(e2e, "_npx_available", lambda: True)
    monkeypatch.setattr(e2e.subprocess, "run", playwright_failed)
    assert e2e.run(["--url", "https://example.com"]) == 1
    body = e2e.REPORT_MD.read_text()
    assert "FAILED" in body
    assert "playwright-report" in body


def test_meta_carries_the_emit_contract():
    assert e2e.META["report_path"] == str(e2e.REPORT_MD)
    assert e2e.META["comment_discriminator"].startswith("## ")
    assert "reliability" in e2e.META["issue_labels"]
