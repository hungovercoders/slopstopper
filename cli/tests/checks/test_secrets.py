"""Tests for the security:secrets check (gitleaks wrapper)."""

from __future__ import annotations

import json

from slopstopper.checks import secrets


SAMPLE_FINDINGS = [
    {
        "RuleID": "aws-access-key",
        "Description": "AWS access key found",
        "File": "src/leak.py",
        "StartLine": 12,
        "Commit": "abcdef1234567890",
    },
    {
        "ruleID": "github-token",
        "description": "GitHub token with very long descriptive text " + ("x" * 80),
        "file": "src/other.py",
        "startLine": 99,
        "commit": "",
    },
]


def test_format_finding_row_uses_capitalized_keys():
    row = secrets._format_finding_row(SAMPLE_FINDINGS[0])
    assert "aws-access-key" in row
    assert "src/leak.py:12" in row
    assert "abcdef12" in row  # short commit


def test_format_finding_row_handles_lowercase_keys_and_working_tree():
    row = secrets._format_finding_row(SAMPLE_FINDINGS[1])
    assert "github-token" in row
    assert "src/other.py:99" in row
    assert "working tree" in row


def test_format_finding_row_truncates_long_description():
    row = secrets._format_finding_row(SAMPLE_FINDINGS[1])
    # Truncation marker
    assert "..." in row


def test_build_md_report_clean():
    md = secrets._build_md_report([])
    assert "✅ Secrets Status" in md
    assert "No secrets detected" in md
    assert "| Rule |" not in md  # no findings table


def test_build_md_report_with_findings():
    md = secrets._build_md_report(SAMPLE_FINDINGS)
    assert "2 secret(s) detected" in md
    assert "| Rule | Location |" in md
    assert "aws-access-key" in md
    assert "github-token" in md


def test_read_findings_empty_when_file_missing(isolated_cwd):
    assert secrets._read_findings() == []


def test_read_findings_handles_null_payload(isolated_cwd):
    secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    secrets.REPORT_JSON.write_text("null")
    assert secrets._read_findings() == []


def test_read_findings_handles_empty_payload(isolated_cwd):
    secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    secrets.REPORT_JSON.write_text("")
    assert secrets._read_findings() == []


def test_read_findings_parses_list_payload(isolated_cwd):
    secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    secrets.REPORT_JSON.write_text(json.dumps(SAMPLE_FINDINGS))
    out = secrets._read_findings()
    assert len(out) == 2


def test_read_findings_returns_empty_on_dict_payload(isolated_cwd):
    secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    secrets.REPORT_JSON.write_text(json.dumps({"oops": "not a list"}))
    assert secrets._read_findings() == []


def test_gitleaks_available_uses_shutil_which(monkeypatch):
    monkeypatch.setattr(secrets.shutil, "which", lambda _: "/usr/bin/gitleaks")
    assert secrets._gitleaks_available() is True

    monkeypatch.setattr(secrets.shutil, "which", lambda _: None)
    assert secrets._gitleaks_available() is False


def test_run_returns_one_when_gitleaks_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(secrets, "_gitleaks_available", lambda: False)
    rc = secrets.run()
    assert rc == 1
    assert "gitleaks is not installed" in capsys.readouterr().out


def test_run_clean_path_when_no_findings(monkeypatch, isolated_cwd, capsys):
    def fake_gitleaks():
        secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        secrets.REPORT_JSON.write_text("null")

    monkeypatch.setattr(secrets, "_gitleaks_available", lambda: True)
    monkeypatch.setattr(secrets, "_run_gitleaks", fake_gitleaks)
    rc = secrets.run()
    assert rc == 0
    md = secrets.REPORT_MD.read_text()
    assert "No secrets detected" in md
    assert "✅ No secrets detected" in capsys.readouterr().out


def test_run_with_findings_returns_zero_but_reports_count(monkeypatch, isolated_cwd, capsys):
    def fake_gitleaks():
        secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        secrets.REPORT_JSON.write_text(json.dumps(SAMPLE_FINDINGS))

    monkeypatch.setattr(secrets, "_gitleaks_available", lambda: True)
    monkeypatch.setattr(secrets, "_run_gitleaks", fake_gitleaks)
    rc = secrets.run()
    # CLI matches bash: returns 0 even when findings present (gating
    # happens at the workflow level via summary scan, not via exit code).
    assert rc == 0
    out = capsys.readouterr().out
    assert "Found 2 secret(s)" in out
    md = secrets.REPORT_MD.read_text()
    assert "aws-access-key" in md
