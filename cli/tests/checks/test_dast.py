"""Tests for the security:dast check (OWASP ZAP wrapper)."""

from __future__ import annotations

import json

from slopstopper.checks import dast


HIGH_ALERT = {
    "name": "SQL Injection",
    "riskcode": "3",
    "confidence": 3,
    "desc": "SQL injection in /search",
    "instances": [{"uri": "/search"}],
    "solution": "Parameterize queries",
}

MEDIUM_ALERT = {
    "name": "Content Security Policy Missing",
    "riskcode": "2",
    "confidence": 2,
    "desc": "No CSP header",
    "instances": [{"uri": "/"}],
    "solution": "Add CSP",
}

LOW_ALERT = {
    "name": "Cookie No HttpOnly",
    "riskcode": "1",
    "confidence": 2,
    "desc": "Cookie missing HttpOnly",
    "instances": [{"uri": "/"}, {"uri": "/login"}],
    "solution": "Set HttpOnly",
}

INFO_ALERT = {
    "name": "Informational X",
    "riskcode": "0",
    "confidence": 1,
    "desc": "FYI only",
    "instances": [{"uri": "/"}],
    "solution": "n/a",
}


def _zap_payload(*alerts: dict) -> dict:
    return {"site": [{"@name": "http://test", "alerts": list(alerts)}]}


# ── helpers ──────────────────────────────────────────────────────


def test_parse_args_defaults_to_localhost():
    parsed = dast._parse_args(None)
    assert parsed.target == dast.DEFAULT_TARGET


def test_parse_args_accepts_explicit_target():
    parsed = dast._parse_args(["--target", "https://staging.example.com"])
    assert parsed.target == "https://staging.example.com"


def test_target_is_localhost_recognises_variants():
    assert dast._target_is_localhost("http://localhost:8080") is True
    assert dast._target_is_localhost("http://127.0.0.1:3000") is True
    assert dast._target_is_localhost("https://example.com") is False


def test_docker_host_target_macos(monkeypatch):
    monkeypatch.setattr(dast.platform, "system", lambda: "Darwin")
    assert dast._docker_host_target("http://localhost:8080") == "http://host.docker.internal:8080"


def test_docker_host_target_linux(monkeypatch):
    monkeypatch.setattr(dast.platform, "system", lambda: "Linux")
    assert dast._docker_host_target("http://localhost:8080") == "http://172.17.0.1:8080"


def test_docker_host_target_preserves_non_default_port(monkeypatch):
    monkeypatch.setattr(dast.platform, "system", lambda: "Linux")
    assert dast._docker_host_target("http://localhost:3000") == "http://172.17.0.1:3000"


def test_docker_host_target_defaults_port_when_omitted(monkeypatch):
    monkeypatch.setattr(dast.platform, "system", lambda: "Linux")
    assert dast._docker_host_target("http://localhost") == "http://172.17.0.1:8080"


def test_collect_alerts_buckets_by_riskcode():
    data = _zap_payload(HIGH_ALERT, MEDIUM_ALERT, LOW_ALERT, INFO_ALERT)
    alerts = dast._collect_alerts(data)
    assert [a["name"] for a in alerts["3"]] == ["SQL Injection"]
    assert [a["name"] for a in alerts["2"]] == ["Content Security Policy Missing"]
    assert [a["name"] for a in alerts["1"]] == ["Cookie No HttpOnly"]
    assert [a["name"] for a in alerts["0"]] == ["Informational X"]


def test_collect_alerts_counts_instances():
    data = _zap_payload(LOW_ALERT)
    alerts = dast._collect_alerts(data)
    assert alerts["1"][0]["instances"] == 2


def test_collect_alerts_normalises_newlines_in_desc():
    multi = {**HIGH_ALERT, "desc": "line one\nline two"}
    alerts = dast._collect_alerts(_zap_payload(multi))
    assert alerts["3"][0]["desc"] == "line one line two"


def test_collect_alerts_empty():
    assert dast._collect_alerts({}) == {"3": [], "2": [], "1": [], "0": []}


def test_format_alert_row_truncates_long_desc():
    long = {**dast._collect_alerts(_zap_payload(HIGH_ALERT))["3"][0], "desc": "x" * 200}
    row = dast._format_alert_row(long)
    assert "..." in row
    assert "SQL Injection" in row
    assert "High" in row


def test_format_alert_section_renders_table():
    alerts = dast._collect_alerts(_zap_payload(HIGH_ALERT))["3"]
    section = dast._format_alert_section(alerts, "High Risk Alerts", "🔴")
    assert "🔴 High Risk Alerts" in section
    assert "| Alert | Risk | Instances | Description |" in section
    assert "SQL Injection" in section


def test_format_alert_section_empty():
    assert dast._format_alert_section([], "Heading", "ICON") == ""


def test_build_md_report_clean():
    md = dast._build_md_report({"site": []})
    assert "✅ DAST Status" in md
    assert "No alerts detected" in md


def test_build_md_report_with_findings_counts_by_severity():
    md = dast._build_md_report(_zap_payload(HIGH_ALERT, MEDIUM_ALERT, LOW_ALERT, INFO_ALERT))
    assert "| 🔴 High | 1 |" in md
    assert "| 🟡 Medium | 1 |" in md
    assert "| 🔵 Low | 1 |" in md
    assert "| ℹ️ Informational | 1 |" in md
    assert "| **Total** | **4** |" in md
    assert "🔴 High Risk Alerts" in md
    assert "🟡 Medium Risk Alerts" in md


# ── subprocess / runtime ─────────────────────────────────────────


def test_docker_available_via_which(monkeypatch):
    monkeypatch.setattr(dast.shutil, "which", lambda _: "/usr/bin/docker")
    assert dast._docker_available() is True
    monkeypatch.setattr(dast.shutil, "which", lambda _: None)
    assert dast._docker_available() is False


def test_read_data_returns_empty_when_file_missing(isolated_cwd):
    assert dast._read_data() == {}


def test_read_data_handles_malformed_json(isolated_cwd):
    dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    dast.REPORT_JSON.write_text("not json")
    assert dast._read_data() == {}


def test_read_data_parses_payload(isolated_cwd):
    dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    dast.REPORT_JSON.write_text(json.dumps(_zap_payload(HIGH_ALERT)))
    data = dast._read_data()
    assert data["site"][0]["alerts"][0]["name"] == "SQL Injection"


def test_run_returns_one_when_docker_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(dast, "_docker_available", lambda: False)
    rc = dast.run()
    assert rc == 1
    assert "Docker is required" in capsys.readouterr().out


def test_run_returns_one_for_localhost_with_no_server(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_localhost_responding", lambda url="http://localhost:8080": False)
    monkeypatch.setattr(dast, "_start_local_server", lambda: None)
    rc = dast.run(["--target", "http://localhost:8080"])
    assert rc == 1
    assert "Nothing listening" in capsys.readouterr().out


def test_run_clean_when_no_alerts(monkeypatch, isolated_cwd, capsys):
    def fake_zap(_target):
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps({"site": []}))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    rc = dast.run(["--target", "https://example.com"])
    assert rc == 0
    assert "✅ No alerts detected" in capsys.readouterr().out
    assert "No alerts detected" in dast.REPORT_MD.read_text()


def test_run_with_blocking_alerts(monkeypatch, isolated_cwd, capsys):
    def fake_zap(_target):
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps(_zap_payload(HIGH_ALERT, MEDIUM_ALERT, LOW_ALERT)))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    rc = dast.run(["--target", "https://example.com"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Found 2 high/medium" in out
    md = dast.REPORT_MD.read_text()
    assert "SQL Injection" in md
    assert "Content Security Policy Missing" in md


def test_run_with_only_low_or_info(monkeypatch, isolated_cwd, capsys):
    def fake_zap(_target):
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps(_zap_payload(LOW_ALERT, INFO_ALERT)))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    rc = dast.run(["--target", "https://example.com"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Found 2 alert(s) — none high/medium" in out
