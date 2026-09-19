"""Tests for the security:dast check (OWASP ZAP wrapper)."""

from __future__ import annotations

import json

import pytest

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
    def fake_zap(_target, **_kwargs):
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps({"site": []}))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    rc = dast.run(["--target", "https://example.com"])
    assert rc == 0
    assert "✅ No alerts detected" in capsys.readouterr().out
    assert "No alerts detected" in dast.REPORT_MD.read_text()


def test_run_with_blocking_alerts(monkeypatch, isolated_cwd, capsys):
    """run() returns 1 when the gate detects blocking alerts.

    Pre-Phase-2 the gate was external (workflow) so run() always
    exited 0. Post-Phase-2 the gate is wired into the check itself,
    so blocking alerts surface as a non-zero exit. The summary and
    report content are unchanged.
    """
    def fake_zap(_target, **_kwargs):
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps(_zap_payload(HIGH_ALERT, MEDIUM_ALERT, LOW_ALERT)))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    rc = dast.run(["--target", "https://example.com"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "Found 2 high/medium" in out
    assert "blocking finding(s)" in out
    md = dast.REPORT_MD.read_text()
    assert "SQL Injection" in md
    assert "Content Security Policy Missing" in md


def test_run_with_only_low_or_info(monkeypatch, isolated_cwd, capsys):
    def fake_zap(_target, **_kwargs):
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps(_zap_payload(LOW_ALERT, INFO_ALERT)))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    rc = dast.run(["--target", "https://example.com"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Found 2 alert(s) — none high/medium" in out


# ── scan-mode selection (ZAP API scan) ───────────────────────────


def _cmd(*args, **kwargs) -> str:
    return " ".join(dast._zap_command(*args, **kwargs))


def test_baseline_is_the_default_mode():
    """No spec configured → the original site spider, unchanged."""
    cmd = _cmd("http://localhost:8080")
    assert "zap-baseline.py" in cmd
    assert "zap-api-scan.py" not in cmd
    assert "-f openapi" not in cmd
    assert "-t http://localhost:8080" in cmd


def test_spec_switches_to_the_api_scan():
    cmd = _cmd("https://api.example.com", spec="https://api.example.com/openapi.json")
    assert "zap-api-scan.py" in cmd
    assert "zap-baseline.py" not in cmd
    # The spec is ZAP's target in API mode; the URL becomes the host override.
    assert "-t https://api.example.com/openapi.json" in cmd
    assert "-f openapi" in cmd
    assert "-O https://api.example.com" in cmd


def test_host_override_can_be_turned_off():
    cmd = _cmd("https://api.example.com", spec="spec.yaml", host_override=False)
    assert "-O" not in cmd.split()


def test_both_modes_keep_the_report_and_warn_flags():
    for cmd in (_cmd("http://x:8080"), _cmd("http://x:8080", spec="s.json")):
        assert "-J dast-report.json" in cmd
        assert cmd.split()[-1] == "-I"


def test_rules_file_is_mounted_and_passed_in_both_modes(isolated_cwd):
    (isolated_cwd / ".zap").mkdir()
    (isolated_cwd / ".zap/rules.tsv").write_text("10038\tIGNORE\n")
    for cmd in (_cmd("http://x:8080"), _cmd("http://x:8080", spec="s.json")):
        assert "/zap/wrk/.zap:ro" in cmd
        assert "-c .zap/rules.tsv" in cmd


# ── spec resolution ──────────────────────────────────────────────


def test_spec_comes_from_config(write_config):
    write_config("api:\n  openapi:\n    spec: openapi.yaml\n")
    assert dast._resolve_spec(None) == "openapi.yaml"


def test_flag_beats_config(write_config):
    write_config("api:\n  openapi:\n    spec: from-config.yaml\n")
    assert dast._resolve_spec("from-flag.yaml") == "from-flag.yaml"


def test_no_spec_anywhere_is_none(write_config):
    write_config("urls:\n  production: https://x\n")
    assert dast._resolve_spec(None) is None


def test_blank_spec_is_treated_as_unset(write_config):
    write_config("api:\n  openapi:\n    spec: '  '\n")
    assert dast._resolve_spec(None) is None


@pytest.mark.parametrize(
    "spec,is_url",
    [
        ("https://api.example.com/openapi.json", True),
        ("http://localhost:8080/openapi.json", True),
        ("openapi.yaml", False),
        ("docs/api/openapi.json", False),
    ],
)
def test_spec_url_detection(spec, is_url):
    assert dast._spec_is_url(spec) is is_url


# ── local spec staging ───────────────────────────────────────────


def test_local_spec_is_staged_into_the_mounted_report_dir(isolated_cwd):
    """ZAP only sees /zap/wrk/, so a repo file has to be copied in."""
    (isolated_cwd / "openapi.yaml").write_text("openapi: 3.0.0\n")
    staged = dast._stage_spec_file("openapi.yaml")
    assert staged == "/zap/wrk/openapi-spec.yaml"
    assert (dast.REPORT_DIR / "openapi-spec.yaml").read_text() == "openapi: 3.0.0\n"


def test_staged_spec_keeps_the_original_extension(isolated_cwd):
    (isolated_cwd / "spec.json").write_text("{}")
    assert dast._stage_spec_file("spec.json") == "/zap/wrk/openapi-spec.json"


def test_missing_spec_file_stages_nothing(isolated_cwd):
    assert dast._stage_spec_file("nope.yaml") is None


def test_staged_spec_is_cleaned_up(isolated_cwd):
    (isolated_cwd / "openapi.yaml").write_text("openapi: 3.0.0\n")
    dast._stage_spec_file("openapi.yaml")
    dast._cleanup_staged_spec()
    assert not list(dast.REPORT_DIR.glob("openapi-spec.*"))


# ── run() wiring ─────────────────────────────────────────────────


def test_run_fails_clearly_when_the_spec_file_is_missing(
    monkeypatch, isolated_cwd, write_config, capsys
):
    write_config("api:\n  openapi:\n    spec: missing.yaml\n")
    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    rc = dast.run(["--target", "https://api.example.com"])
    assert rc == 1
    assert "OpenAPI spec not found" in capsys.readouterr().out


def test_run_passes_the_spec_through_to_zap(monkeypatch, isolated_cwd, write_config):
    write_config("api:\n  openapi:\n    spec: https://api.example.com/openapi.json\n")
    seen: dict = {}

    def fake_zap(target, **kwargs):
        seen.update(target=target, **kwargs)
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps({"site": []}))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    assert dast.run(["--target", "https://api.example.com"]) == 0
    assert seen["spec"] == "https://api.example.com/openapi.json"
    assert seen["host_override"] is True


def test_run_honours_the_host_override_config(monkeypatch, isolated_cwd, write_config):
    write_config(
        "api:\n  openapi:\n    spec: https://x/openapi.json\n    host_override: false\n"
    )
    seen: dict = {}

    def fake_zap(target, **kwargs):
        seen.update(kwargs)
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps({"site": []}))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    assert dast.run(["--target", "https://x"]) == 0
    assert seen["host_override"] is False


def test_run_without_a_spec_stays_on_baseline(monkeypatch, isolated_cwd, write_config):
    write_config("urls:\n  production: https://example.com\n")
    seen: dict = {}

    def fake_zap(target, **kwargs):
        seen.update(kwargs)
        dast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dast.REPORT_JSON.write_text(json.dumps({"site": []}))

    monkeypatch.setattr(dast, "_docker_available", lambda: True)
    monkeypatch.setattr(dast, "_run_zap", fake_zap)
    assert dast.run(["--target", "https://example.com"]) == 0
    assert seen["spec"] is None
