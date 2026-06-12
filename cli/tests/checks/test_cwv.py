"""Tests for the reliability:cwv check (Lighthouse CI wrapper)."""

from __future__ import annotations

import subprocess

from slopstopper.checks import cwv


# ── helpers ──────────────────────────────────────────────────────


def test_parse_args_defaults():
    parsed = cwv._parse_args(None)
    assert parsed.url is None
    assert parsed.config == str(cwv.LHCI_CONFIG)


def test_parse_args_explicit():
    parsed = cwv._parse_args(["--url", "https://example.com", "--config", "custom.json"])
    assert parsed.url == "https://example.com"
    assert parsed.config == "custom.json"


def test_resolve_url_prefers_flag(monkeypatch):
    monkeypatch.setenv("CWV_URL", "https://from-env")
    assert cwv._resolve_url("https://from-flag") == "https://from-flag"


def test_resolve_url_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("CWV_URL", "https://from-env")
    assert cwv._resolve_url(None) == "https://from-env"


def test_resolve_url_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("CWV_URL", raising=False)
    assert cwv._resolve_url(None) is None


def test_build_cmd_threads_url_and_config():
    cmd = cwv._build_cmd("https://example.com", "myconf.json")
    assert cmd[:3] == ["npx", "lhci", "autorun"]
    assert "--collect.url=https://example.com" in cmd
    assert "--config=myconf.json" in cmd


# ── subprocess / runtime ─────────────────────────────────────────


def test_npx_available_via_which(monkeypatch):
    monkeypatch.setattr(cwv.shutil, "which", lambda _: "/usr/bin/npx")
    assert cwv._npx_available() is True
    monkeypatch.setattr(cwv.shutil, "which", lambda _: None)
    assert cwv._npx_available() is False


def test_run_returns_one_when_npx_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(cwv, "_npx_available", lambda: False)
    rc = cwv.run()
    assert rc == 1
    assert "npx is not available" in capsys.readouterr().out


def test_run_returns_one_when_url_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(cwv, "_npx_available", lambda: True)
    monkeypatch.delenv("CWV_URL", raising=False)
    rc = cwv.run([])
    assert rc == 1
    assert "CWV target URL is required" in capsys.readouterr().out


def test_run_returns_one_when_config_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(cwv, "_npx_available", lambda: True)
    rc = cwv.run(["--url", "https://example.com"])
    assert rc == 1
    assert "Lighthouse CI config not found" in capsys.readouterr().out


def test_run_invokes_lhci_with_expected_args(monkeypatch, isolated_cwd):
    cwv.LHCI_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    cwv.LHCI_CONFIG.write_text("{}")

    captured: dict = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cwv, "_npx_available", lambda: True)
    monkeypatch.setattr(cwv.subprocess, "run", fake_run)

    rc = cwv.run(["--url", "https://example.com"])
    assert rc == 0
    assert captured["cmd"][:3] == ["npx", "lhci", "autorun"]
    assert "--collect.url=https://example.com" in captured["cmd"]
    assert f"--config={cwv.LHCI_CONFIG}" in captured["cmd"]


def test_run_propagates_lhci_failure(monkeypatch, isolated_cwd):
    cwv.LHCI_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    cwv.LHCI_CONFIG.write_text("{}")

    monkeypatch.setattr(cwv, "_npx_available", lambda: True)
    monkeypatch.setattr(
        cwv.subprocess, "run",
        lambda cmd, check: subprocess.CompletedProcess(cmd, 1),
    )

    rc = cwv.run(["--url", "https://example.com"])
    assert rc == 1


def test_run_accepts_explicit_config(monkeypatch, isolated_cwd):
    custom = isolated_cwd / "custom-lhci.json"
    custom.write_text("{}")

    captured: dict = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cwv, "_npx_available", lambda: True)
    monkeypatch.setattr(cwv.subprocess, "run", fake_run)

    rc = cwv.run(["--url", "https://example.com", "--config", str(custom)])
    assert rc == 0
    assert f"--config={custom}" in captured["cmd"]
