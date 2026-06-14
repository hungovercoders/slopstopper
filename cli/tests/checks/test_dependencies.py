"""Tests for the security:dependencies check (trivy wrapper)."""

from __future__ import annotations

import json

from slopstopper.checks import dependencies


CRITICAL_VULN = {
    "VulnerabilityID": "CVE-2024-0001",
    "PkgName": "left-pad",
    "InstalledVersion": "1.0.0",
    "FixedVersion": "1.0.1",
    "Severity": "CRITICAL",
    "Title": "Remote code execution",
}

HIGH_VULN = {
    "VulnerabilityID": "CVE-2024-0002",
    "PkgName": "lodash",
    "InstalledVersion": "4.17.20",
    "FixedVersion": "4.17.21",
    "Severity": "HIGH",
    "Title": "Prototype pollution",
}

MEDIUM_VULN = {
    "VulnerabilityID": "CVE-2024-0003",
    "PkgName": "axios",
    "InstalledVersion": "0.21.0",
    "FixedVersion": "0.21.4",
    "Severity": "MEDIUM",
    "Title": "SSRF",
}

LOW_VULN = {
    "VulnerabilityID": "CVE-2024-0004",
    "PkgName": "minimist",
    "InstalledVersion": "1.2.0",
    "FixedVersion": "1.2.6",
    "Severity": "LOW",
    "Title": "Minor issue",
}


def _trivy_payload(*vulns: dict, target: str = "package-lock.json") -> dict:
    return {"Results": [{"Target": target, "Vulnerabilities": list(vulns)}]}


# ── helpers ──────────────────────────────────────────────────────


def test_collect_vulnerabilities_buckets_by_severity():
    data = _trivy_payload(CRITICAL_VULN, HIGH_VULN, MEDIUM_VULN, LOW_VULN)
    critical, high, medium, low = dependencies._collect_vulnerabilities(data)
    assert [v["id"] for v in critical] == ["CVE-2024-0001"]
    assert [v["id"] for v in high] == ["CVE-2024-0002"]
    assert [v["id"] for v in medium] == ["CVE-2024-0003"]
    assert [v["id"] for v in low] == ["CVE-2024-0004"]


def test_collect_vulnerabilities_unknown_severity_lands_in_low():
    odd = {**HIGH_VULN, "Severity": "UNKNOWN"}
    critical, high, medium, low = dependencies._collect_vulnerabilities(_trivy_payload(odd))
    assert critical == [] and high == [] and medium == []
    assert len(low) == 1


def test_collect_vulnerabilities_missing_fields_defaults():
    data = _trivy_payload({"Severity": "HIGH"})
    _, high, _, _ = dependencies._collect_vulnerabilities(data)
    assert high[0]["id"] == "unknown"
    assert high[0]["pkg"] == "unknown"
    assert high[0]["installed"] == "?"
    assert high[0]["fixed"] == "none"


def test_collect_vulnerabilities_empty_data():
    assert dependencies._collect_vulnerabilities({}) == ([], [], [], [])
    assert dependencies._collect_vulnerabilities({"Results": []}) == ([], [], [], [])


def test_format_vuln_row_truncates_long_title():
    long = {
        **dependencies._collect_vulnerabilities(_trivy_payload(HIGH_VULN))[1][0],
        "title": "x" * 200,
    }
    row = dependencies._format_vuln_row(long)
    assert "..." in row
    assert "lodash" in row


def test_format_vuln_section_renders_table():
    vulns = dependencies._collect_vulnerabilities(_trivy_payload(CRITICAL_VULN))[0]
    section = dependencies._format_vuln_section(vulns, "Critical Vulnerabilities", "🔴")
    assert "🔴 Critical Vulnerabilities" in section
    assert "| CVE | Package | Installed | Fixed In | Severity | Title |" in section
    assert "CVE-2024-0001" in section


def test_format_vuln_section_empty():
    assert dependencies._format_vuln_section([], "Heading", "ICON") == ""


def test_build_md_report_clean():
    md = dependencies._build_md_report({"Results": []})
    assert "✅ Dependencies Status" in md
    assert "No vulnerabilities detected" in md


def test_build_md_report_with_findings_counts_by_severity():
    data = _trivy_payload(CRITICAL_VULN, HIGH_VULN, MEDIUM_VULN, LOW_VULN)
    md = dependencies._build_md_report(data)
    assert "| 🔴 Critical | 1 |" in md
    assert "| 🟠 High | 1 |" in md
    assert "| 🟡 Medium | 1 |" in md
    assert "| 🔵 Low | 1 |" in md
    assert "| **Total** | **4** |" in md
    assert "🔴 Critical Vulnerabilities" in md
    assert "🟠 High Vulnerabilities" in md


# ── subprocess / runtime ─────────────────────────────────────────


def test_trivy_available_via_which(monkeypatch):
    monkeypatch.setattr(dependencies.shutil, "which", lambda _: "/usr/bin/trivy")
    assert dependencies._trivy_available() is True
    monkeypatch.setattr(dependencies.shutil, "which", lambda _: None)
    assert dependencies._trivy_available() is False


def test_read_data_returns_empty_when_file_missing(isolated_cwd):
    assert dependencies._read_data() == {}


def test_read_data_handles_malformed_json(isolated_cwd):
    dependencies.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    dependencies.REPORT_JSON.write_text("not json")
    assert dependencies._read_data() == {}


def test_read_data_parses_payload(isolated_cwd):
    dependencies.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    dependencies.REPORT_JSON.write_text(json.dumps(_trivy_payload(HIGH_VULN)))
    data = dependencies._read_data()
    assert data["Results"][0]["Target"] == "package-lock.json"


def test_run_returns_one_when_trivy_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(dependencies, "_trivy_available", lambda: False)
    rc = dependencies.run()
    assert rc == 1
    assert "trivy is not installed" in capsys.readouterr().out


def test_run_clean_when_no_vulns(monkeypatch, isolated_cwd, capsys):
    def fake_trivy():
        dependencies.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dependencies.REPORT_JSON.write_text(json.dumps({"Results": []}))

    monkeypatch.setattr(dependencies, "_trivy_available", lambda: True)
    monkeypatch.setattr(dependencies, "_run_trivy", fake_trivy)
    rc = dependencies.run()
    assert rc == 0
    assert "✅ No vulnerabilities detected" in capsys.readouterr().out
    assert "No vulnerabilities detected" in dependencies.REPORT_MD.read_text()


def test_run_exits_two_on_critical_or_high(monkeypatch, isolated_cwd, capsys):
    """Local/CI gate parity: HIGH+ findings make this check exit non-zero
    so adopters' local `task ss:security:vulnerability:all` agrees with
    the CI workflow without a separate post-processing gate step."""

    def fake_trivy():
        dependencies.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dependencies.REPORT_JSON.write_text(
            json.dumps(_trivy_payload(CRITICAL_VULN, HIGH_VULN, MEDIUM_VULN))
        )

    monkeypatch.setattr(dependencies, "_trivy_available", lambda: True)
    monkeypatch.setattr(dependencies, "_run_trivy", fake_trivy)
    rc = dependencies.run()
    assert rc == 2, "CRITICAL+HIGH findings must produce a non-zero exit code"
    out = capsys.readouterr().out
    assert "Found 2 CRITICAL/HIGH" in out
    md = dependencies.REPORT_MD.read_text()
    assert "CVE-2024-0001" in md
    assert "CVE-2024-0002" in md


def test_run_with_only_medium_or_low(monkeypatch, isolated_cwd, capsys):
    """MEDIUM/LOW only → exit 0 (still reported, but doesn't block)."""

    def fake_trivy():
        dependencies.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        dependencies.REPORT_JSON.write_text(
            json.dumps(_trivy_payload(MEDIUM_VULN, LOW_VULN))
        )

    monkeypatch.setattr(dependencies, "_trivy_available", lambda: True)
    monkeypatch.setattr(dependencies, "_run_trivy", fake_trivy)
    rc = dependencies.run()
    assert rc == 0
    out = capsys.readouterr().out
    assert "Found 2 vulnerability(ies) — none CRITICAL/HIGH" in out
