"""Tests for the security:sast check (semgrep wrapper)."""

from __future__ import annotations

import json

from slopstopper.checks import sast


ERROR_FINDING = {
    "check_id": "rule.x.error",
    "path": "src/risky.py",
    "start": {"line": 42, "col": 1, "offset": 0},
    "extra": {"severity": "ERROR", "message": "Hardcoded secret detected"},
}

WARNING_FINDING = {
    "check_id": "rule.y.warning",
    "path": "src/other.py",
    "start": {"line": 99, "col": 1, "offset": 0},
    "extra": {"severity": "WARNING", "message": "Possibly unsafe call"},
}

INFO_FINDING = {
    "check_id": "rule.z.info",
    "path": "src/log.py",
    "start": {"line": 5},
    "extra": {"severity": "INFO", "message": "Informational"},
}


# ── helpers ──────────────────────────────────────────────────────


def test_categorize_findings_buckets_by_uppercase_severity():
    errors, warnings = sast._categorize_findings([ERROR_FINDING, WARNING_FINDING, INFO_FINDING])
    assert errors == [ERROR_FINDING]
    # WARNING + INFO both bucket as warnings (non-ERROR)
    assert warnings == [WARNING_FINDING, INFO_FINDING]


def test_format_finding_row_truncates_long_message():
    long = {
        **ERROR_FINDING,
        "extra": {"severity": "ERROR", "message": "x" * 200},
    }
    row = sast._format_finding_row(long)
    assert "..." in row
    assert "src/risky.py:42" in row


def test_format_finding_row_normalises_newlines():
    multi = {
        **WARNING_FINDING,
        "extra": {"severity": "WARNING", "message": "line one\nline two"},
    }
    row = sast._format_finding_row(multi)
    assert "\n" not in row.replace("\n", "", 0)  # row itself is one line
    # the newline in message was replaced with space
    assert "line one line two" in row


def test_format_findings_section_renders_table():
    section = sast._format_findings_section([ERROR_FINDING], "Error Findings", "🔴")
    assert "🔴 Error Findings" in section
    assert "| Rule | Severity | Location | Message |" in section
    assert "rule.x.error" in section


def test_format_findings_section_empty():
    assert sast._format_findings_section([], "Heading", "ICON") == ""


def test_collect_parsing_errors_picks_yaml_partial_parse():
    errors = [
        {
            "type": ["PartialParsing"],
            "path": ".github/workflows/x.yml",
            "spans": [{"start": {"line": 12}}],
        },
        {"type": ["OtherType"], "path": "irrelevant"},  # ignored
    ]
    out = sast._collect_parsing_errors(errors)
    assert ".github/workflows/x.yml" in out
    assert 12 in out[".github/workflows/x.yml"]
    assert "irrelevant" not in out


def test_format_scan_errors_explanation_yaml_path():
    errors = [
        {"type": ["PartialParsing"], "path": ".github/workflows/x.yml",
         "spans": [{"start": {"line": 1}}]},
        {"type": ["PartialParsing"], "path": ".github/workflows/y.yml",
         "spans": [{"start": {"line": 2}}]},
    ]
    out = sast._format_scan_errors_explanation(errors)
    assert "parsing errors in YAML workflow files" in out
    assert "`.github/workflows/x.yml`" in out
    assert "Safe to ignore" in out or "safe to ignore" in out.lower()


def test_format_scan_errors_explanation_generic_path():
    errors = [{"type": ["Random"], "path": "x.py", "message": "Something broke"}]
    out = sast._format_scan_errors_explanation(errors)
    assert "Semgrep reported 1 error(s)" in out
    assert "Something broke" in out


def test_format_scan_errors_explanation_empty():
    assert sast._format_scan_errors_explanation([]) == ""


def test_build_md_report_clean():
    md = sast._build_md_report({"results": [], "errors": []})
    assert "✅ SAST Status" in md
    assert "No findings detected" in md


def test_build_md_report_with_findings_counts_severities():
    md = sast._build_md_report({"results": [ERROR_FINDING, WARNING_FINDING], "errors": []})
    assert "| Total findings | 2 |" in md
    assert "| Errors | 1 |" in md
    assert "| Warnings | 1 |" in md
    assert "🔴 Error Findings" in md
    assert "⚠️ Warning Findings" in md


def test_build_md_report_includes_errors_summary():
    md = sast._build_md_report({
        "results": [],
        "errors": [{"type": ["PartialParsing"], "path": "x.yml", "spans": [{"start": {"line": 1}}]}],
    })
    assert "Semgrep encountered 1 scan error(s)" in md
    assert "parsing errors in YAML" in md


# ── subprocess / runtime ─────────────────────────────────────────


def test_semgrep_available_via_which(monkeypatch):
    monkeypatch.setattr(sast.shutil, "which", lambda _: "/usr/bin/semgrep")
    assert sast._semgrep_available() is True
    monkeypatch.setattr(sast.shutil, "which", lambda _: None)
    assert sast._semgrep_available() is False


def test_read_data_returns_empty_when_file_missing(isolated_cwd):
    assert sast._read_data() == {"results": [], "errors": []}


def test_read_data_handles_malformed_json(isolated_cwd):
    sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    sast.REPORT_JSON.write_text("not json")
    assert sast._read_data() == {"results": [], "errors": []}


def test_read_data_parses_payload(isolated_cwd):
    sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    sast.REPORT_JSON.write_text(json.dumps({"results": [ERROR_FINDING], "errors": []}))
    data = sast._read_data()
    assert data["results"] == [ERROR_FINDING]


def test_run_returns_one_when_semgrep_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(sast, "_semgrep_available", lambda: False)
    rc = sast.run()
    assert rc == 1
    assert "semgrep is not installed" in capsys.readouterr().out


def test_run_clean_when_no_results(monkeypatch, isolated_cwd, capsys):
    def fake_semgrep():
        sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        sast.REPORT_JSON.write_text(json.dumps({"results": [], "errors": []}))

    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)
    monkeypatch.setattr(sast, "_run_semgrep", fake_semgrep)
    rc = sast.run()
    assert rc == 0
    assert "✅ No findings detected" in capsys.readouterr().out
    assert "No findings detected" in sast.REPORT_MD.read_text()


def test_run_with_findings_returns_zero_and_writes_report(monkeypatch, isolated_cwd, capsys):
    def fake_semgrep():
        sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        sast.REPORT_JSON.write_text(json.dumps(
            {"results": [ERROR_FINDING, WARNING_FINDING], "errors": []}
        ))

    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)
    monkeypatch.setattr(sast, "_run_semgrep", fake_semgrep)
    rc = sast.run()
    # Bash flow returns 0 even with findings; gating happens elsewhere.
    assert rc == 0
    out = capsys.readouterr().out
    assert "Found 2 finding(s)" in out
    md = sast.REPORT_MD.read_text()
    assert "rule.x.error" in md
    assert "rule.y.warning" in md
