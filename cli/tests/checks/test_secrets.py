"""Tests for the security:secrets check (gitleaks wrapper)."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

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


# ── redaction ────────────────────────────────────────────────────
#
# Gitleaks' native JSON carries the credential itself (`Secret`) and the
# source text around it (`Match`, `Line`). Both reports are uploaded as
# CI artifacts that anyone with read access can download, so the JSON
# must be scrubbed on disk before anything else can pick it up.

# A well-formed fake GitHub PAT. The real gitleaks binary must flag it inside
# the temp repo the end-to-end test builds, so it has to look real; the
# `github-pat` rule is a plain regex that is stable across gitleaks 8.21–8.30
# (the AWS rule is not — 8.30 stopped flagging a bare AKIA… id). GitHub's own
# push protection checksums PATs, so a random one is never mistaken for live.
# Defined exactly once, on a line gitleaks is told to skip, because the
# secrets workflow scans every branch's history and would otherwise fail
# every open PR on this fixture.
PLANTED_KEY = "ghp_ujOeHwdFcAefAZhnM6Jy8c1rihtYlKNxHddm"  # gitleaks:allow

RAW_FINDING = {
    "RuleID": "github-pat",
    "Description": "GitHub personal access token",
    "File": "config/prod.env",
    "StartLine": 12,
    "EndLine": 12,
    "Commit": "abcdef1234567890",
    "Fingerprint": "abcdef1234567890:config/prod.env:github-pat:12",
    "Secret": PLANTED_KEY,
    "Match": f"GITHUB_TOKEN={PLANTED_KEY}",
    "Line": f"export GITHUB_TOKEN={PLANTED_KEY}",
    "Entropy": 3.5,
}


def test_redact_finding_strips_credential_bearing_keys():
    redacted = secrets._redact_finding(RAW_FINDING)
    assert "Secret" not in redacted
    assert "Match" not in redacted
    assert "Line" not in redacted
    # Everything a human needs to find and fix it survives.
    assert redacted["RuleID"] == "github-pat"
    assert redacted["File"] == "config/prod.env"
    assert redacted["StartLine"] == 12
    assert redacted["Commit"] == "abcdef1234567890"
    assert redacted["Fingerprint"].startswith("abcdef12")


def test_redact_finding_is_case_insensitive():
    lower = {"ruleID": "x", "secret": "s", "match": "m", "line": "l", "file": "f"}
    redacted = secrets._redact_finding(lower)
    assert set(redacted) == {"ruleID", "file"}


def test_redact_findings_leaves_non_dict_entries_alone():
    assert secrets._redact_findings(["not a dict", RAW_FINDING])[0] == "not a dict"


def test_run_rewrites_the_json_on_disk_without_secret_values(monkeypatch, isolated_cwd):
    def fake_gitleaks():
        secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        secrets.REPORT_JSON.write_text(json.dumps([RAW_FINDING]))

    monkeypatch.setattr(secrets, "_gitleaks_available", lambda: True)
    monkeypatch.setattr(secrets, "_run_gitleaks", fake_gitleaks)
    assert secrets.run() == 0

    on_disk = secrets.REPORT_JSON.read_text()
    assert PLANTED_KEY not in on_disk
    assert '"Secret"' not in on_disk
    assert '"Match"' not in on_disk
    # The workflow gate counts list length — the shape must survive.
    assert len(json.loads(on_disk)) == 1
    assert PLANTED_KEY not in secrets.REPORT_MD.read_text()


def test_run_rewrites_a_malformed_report_rather_than_leaving_it(monkeypatch, isolated_cwd):
    """An unparseable report is still a file that may hold a secret."""

    def fake_gitleaks():
        secrets.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        secrets.REPORT_JSON.write_text('[{"Secret": "' + PLANTED_KEY + '"')  # truncated

    monkeypatch.setattr(secrets, "_gitleaks_available", lambda: True)
    monkeypatch.setattr(secrets, "_run_gitleaks", fake_gitleaks)
    assert secrets.run() == 0
    assert PLANTED_KEY not in secrets.REPORT_JSON.read_text()


def test_write_redacted_json_does_not_create_a_file_gitleaks_never_wrote(isolated_cwd):
    secrets._write_redacted_json([])
    assert not secrets.REPORT_JSON.exists()


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not on PATH")
def test_real_gitleaks_output_is_redacted_end_to_end(isolated_cwd):
    """Plant a token, run the real binary, prove it never reaches disk."""
    planted = PLANTED_KEY
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "init", "-q", "."], check=True)
    (isolated_cwd / "config.env").write_text(f"GITHUB_TOKEN={planted}\n")
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "leak"], check=True)

    assert secrets.run() == 0

    findings = json.loads(secrets.REPORT_JSON.read_text())
    assert len(findings) >= 1, "gitleaks should have flagged the planted key"
    for finding in findings:
        assert "Secret" not in finding
        assert "Match" not in finding
        assert "Line" not in finding
    assert planted not in secrets.REPORT_JSON.read_text()
    assert planted not in secrets.REPORT_MD.read_text()
    # The redacted report still says where to look.
    assert findings[0]["File"] == "config.env"
    assert findings[0]["StartLine"] == 1
