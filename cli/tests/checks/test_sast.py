"""Tests for the security:sast check (semgrep wrapper)."""

from __future__ import annotations

import json

import pytest

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


def test_read_data_is_none_when_file_missing(isolated_cwd):
    assert sast._read_data() is None


def test_read_data_is_none_for_malformed_json(isolated_cwd):
    sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    sast.REPORT_JSON.write_text("not json")
    assert sast._read_data() is None


def test_read_data_parses_payload(isolated_cwd):
    sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    sast.REPORT_JSON.write_text(json.dumps({"results": [ERROR_FINDING], "errors": []}))
    data = sast._read_data()
    assert data["results"] == [ERROR_FINDING]


def test_run_returns_two_when_semgrep_missing(monkeypatch, isolated_cwd, capsys):
    """A missing tool is 'could not run', not 'the repo failed'."""
    monkeypatch.setattr(sast, "_semgrep_available", lambda: False)
    monkeypatch.setattr(sast, "_rules", lambda: (sast.REGISTRY, None))
    rc = sast.run()
    assert rc == 2
    assert "semgrep is not installed" in capsys.readouterr().out


def test_run_clean_when_no_results(monkeypatch, isolated_cwd, capsys):
    def fake_semgrep(rules=None):
        sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        sast.REPORT_JSON.write_text(json.dumps({"results": [], "errors": []}))
        return 0

    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)

    monkeypatch.setattr(sast, "_rules", lambda: (sast.REGISTRY, None))
    monkeypatch.setattr(sast, "_run_semgrep", fake_semgrep)
    rc = sast.run()
    assert rc == 0
    assert "✅ No findings detected" in capsys.readouterr().out
    assert "No findings detected" in sast.REPORT_MD.read_text()


def _stub_semgrep(monkeypatch, *findings):
    def fake_semgrep(rules=None):
        sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        sast.REPORT_JSON.write_text(json.dumps({"results": list(findings), "errors": []}))
        return 0

    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)

    monkeypatch.setattr(sast, "_rules", lambda: (sast.REGISTRY, None))
    monkeypatch.setattr(sast, "_run_semgrep", fake_semgrep)


def test_run_with_an_error_finding_returns_one_and_writes_report(monkeypatch, isolated_cwd, capsys):
    """The check is the gate. The workflow used to re-derive this from the
    JSON in a Python heredoc; now the exit code is the verdict."""
    _stub_semgrep(monkeypatch, ERROR_FINDING, WARNING_FINDING)
    rc = sast.run()
    assert rc == 1
    out = capsys.readouterr().out
    assert "Found 2 finding(s)" in out
    assert "1 finding(s) at or above `fail_on: error`" in out
    md = sast.REPORT_MD.read_text()
    assert "rule.x.error" in md
    assert "rule.y.warning" in md


def test_warnings_alone_do_not_fail_by_default(monkeypatch, isolated_cwd, capsys):
    _stub_semgrep(monkeypatch, WARNING_FINDING)
    assert sast.run() == 0
    assert "none at or above `fail_on: error`" in capsys.readouterr().out


def test_fail_on_warning_makes_warnings_fail(monkeypatch, write_config):
    write_config("security:\n  sast:\n    fail_on: warning\n")
    _stub_semgrep(monkeypatch, WARNING_FINDING)
    assert sast.run() == 1


def test_fail_on_none_never_fails(monkeypatch, write_config):
    write_config("security:\n  sast:\n    fail_on: none\n")
    _stub_semgrep(monkeypatch, ERROR_FINDING)
    assert sast.run() == 0


def test_unknown_fail_on_warns_and_uses_the_default(monkeypatch, write_config, capsys):
    write_config("security:\n  sast:\n    fail_on: loud\n")
    _stub_semgrep(monkeypatch, WARNING_FINDING)
    assert sast.run() == 0
    assert "not one of error, warning, info, none" in capsys.readouterr().out


def test_blocking_findings_ranks_severities():
    info = {"extra": {"severity": "INFO"}}
    assert sast._blocking_findings([ERROR_FINDING, WARNING_FINDING, info], "error") == [ERROR_FINDING]
    assert sast._blocking_findings([ERROR_FINDING, WARNING_FINDING, info], "warning") == [
        ERROR_FINDING, WARNING_FINDING
    ]
    assert len(sast._blocking_findings([ERROR_FINDING, WARNING_FINDING, info], "info")) == 3
    assert sast._blocking_findings([ERROR_FINDING], "none") == []


# ── review follow-ups ─────────────────────────────────────────────


def test_run_returns_two_when_semgrep_writes_no_report(monkeypatch, isolated_cwd, capsys):
    """A crashed scan is 'could not run', never a clean pass."""
    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)
    monkeypatch.setattr(sast, "_rules", lambda: (sast.REGISTRY, None))
    monkeypatch.setattr(sast, "_run_semgrep", lambda rules=None: 0)
    assert sast.run() == 2
    assert "did not complete" in capsys.readouterr().out
    assert "Scan did not complete" in sast.REPORT_MD.read_text()


def test_run_returns_two_when_the_report_is_malformed(monkeypatch, isolated_cwd):
    def fake_semgrep(rules=None):
        sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        sast.REPORT_JSON.write_text('{"results": [')
        return 0

    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)

    monkeypatch.setattr(sast, "_rules", lambda: (sast.REGISTRY, None))
    monkeypatch.setattr(sast, "_run_semgrep", fake_semgrep)
    assert sast.run() == 2


@pytest.mark.parametrize("severity", ["CRITICAL", "HIGH", "SOMETHING-NEW"])
def test_new_and_unknown_severities_block_by_default(monkeypatch, isolated_cwd, severity):
    """Registry rules may report CRITICAL/HIGH; an unrecognised label must
    not rank below the gate."""
    _stub_semgrep(monkeypatch, {"check_id": "r", "extra": {"severity": severity}})
    assert sast.run() == 1


def test_medium_and_low_rank_as_warning_and_info():
    medium = {"extra": {"severity": "MEDIUM"}}
    low = {"extra": {"severity": "LOW"}}
    assert sast._blocking_findings([medium, low], "error") == []
    assert sast._blocking_findings([medium, low], "warning") == [medium]


def test_fail_on_false_warns_instead_of_silently_defaulting(monkeypatch, write_config, capsys):
    write_config("security:\n  sast:\n    fail_on: false\n")
    _stub_semgrep(monkeypatch, WARNING_FINDING)
    assert sast.run() == 0
    assert "not one of error, warning, info, none" in capsys.readouterr().out


# ── round-3 contract gaps ────────────────────────────────────────


class _Proc:
    def __init__(self, returncode):
        self.returncode = returncode


def test_a_fatal_semgrep_exit_is_not_a_clean_pass(monkeypatch, isolated_cwd, capsys):
    """Semgrep can exit 2/7 yet still write `{"results": [], "errors": [...]}`."""

    def fake_subprocess_run(argv, **kw):
        sast.REPORT_JSON.write_text(json.dumps({"results": [], "errors": [{"level": "error"}]}))
        return _Proc(7)

    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)

    monkeypatch.setattr(sast, "_rules", lambda: (sast.REGISTRY, None))
    monkeypatch.setattr(sast.subprocess, "run", fake_subprocess_run)
    assert sast.run() == 2
    assert "did not complete" in capsys.readouterr().out


def test_a_previous_runs_sast_report_cannot_stand_in_for_this_one(monkeypatch, isolated_cwd):
    sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    sast.REPORT_JSON.write_text(json.dumps({"results": [], "errors": []}))
    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)
    monkeypatch.setattr(sast, "_rules", lambda: (sast.REGISTRY, None))
    monkeypatch.setattr(sast.subprocess, "run", lambda argv, **kw: _Proc(0))  # writes nothing
    assert sast.run() == 2


@pytest.mark.parametrize("severity", ["INVENTORY", "EXPERIMENT"])
def test_non_security_severities_do_not_block_by_default(severity):
    finding = {"check_id": "x", "extra": {"severity": severity}}
    assert sast._blocking_findings([finding], "error") == []


def test_a_finding_with_null_extra_neither_crashes_nor_passes():
    finding = {"check_id": "x", "path": "a.py", "extra": None}
    assert sast._blocking_findings([finding], "error") == [finding]  # fail closed
    assert "unknown" in sast._format_finding_row(finding)


# ── where the rules come from (security.sast.rules) ─────────────
#
# --config=auto logs in to the Semgrep Registry with the repo URL and turns
# metrics on; Semgrep refuses it with --metrics=off. Local rules are the
# only way to run the scan without sending anything.


@pytest.fixture
def semgrep_argv(monkeypatch):
    """Capture the command Semgrep would be run with."""
    calls: list[list[str]] = []

    def fake_run(cmd, check=False):
        calls.append(cmd)
        sast.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        sast.REPORT_JSON.write_text(json.dumps({"results": [], "errors": []}))
        return type("Done", (), {"returncode": 0})()

    monkeypatch.setattr(sast, "_semgrep_available", lambda: True)
    monkeypatch.setattr(sast.subprocess, "run", fake_run)
    return calls


@pytest.mark.parametrize("body", ["", "security:\n  sast:\n    rules: []\n", "security:\n  sast:\n    fail_on: warning\n"])
def test_sast_is_off_until_the_repo_opts_in(write_config, semgrep_argv, monkeypatch, capsys, body):
    """Nothing is scanned or sent by default — sending data to semgrep.dev
    is opt-in. The skip is a pass (exit 0), and it says how to opt in."""
    write_config(body)
    monkeypatch.setattr(sast, "_semgrep_available", lambda: False)  # not even needed
    assert sast.run() == 0
    assert semgrep_argv == []
    md = sast.REPORT_MD.read_text()
    assert "SKIPPED" in md and "SAST is off" in md
    assert "rules: auto" in md and "Sends nothing" in md
    assert "SAST is off" in capsys.readouterr().out


def test_rules_auto_opts_in_to_the_registry(write_config, semgrep_argv, capsys):
    write_config("security:\n  sast:\n    rules: auto\n")
    assert sast.run() == 0
    (cmd,) = semgrep_argv
    assert "--config=auto" in cmd
    assert not any(a.startswith("--metrics") for a in cmd)
    assert "sends the repository URL" in capsys.readouterr().out
    assert "Semgrep Registry" in sast.REPORT_MD.read_text()


@pytest.mark.parametrize("body", [
    "security:\n  sast:\n    rules:\n      - .semgrep/\n      - extra.yml\n",
    "security:\n  sast:\n    rules: .semgrep/, extra.yml\n",
])
def test_local_rules_run_with_metrics_off(write_config, semgrep_argv, body):
    (write_config(body).parent / ".semgrep").mkdir()
    (write_config(body).parent / "extra.yml").write_text("rules: []\n")
    assert sast.run() == 0
    (cmd,) = semgrep_argv
    assert "--config=auto" not in cmd
    assert cmd[1:4] == ["--config=.semgrep/", "--config=extra.yml", "--metrics=off"]
    md = sast.REPORT_MD.read_text()
    assert "local: `.semgrep/`, `extra.yml`" in md and "nothing is sent" in md


@pytest.mark.parametrize("entry", ["p/owasp-top-ten", "r/python.lang.x", "https://example.com/rules.yml", "auto"])
def test_a_remote_entry_is_refused_not_fetched(write_config, semgrep_argv, entry):
    (write_config("x").parent / ".semgrep").mkdir()
    write_config(f"security:\n  sast:\n    rules:\n      - .semgrep/\n      - {entry}\n")
    assert sast.run() == 2
    assert semgrep_argv == [], "semgrep must not run when the rules would be fetched"
    assert "not a local path" in sast.REPORT_MD.read_text()


def test_a_missing_rules_path_is_could_not_run(write_config, semgrep_argv):
    write_config("security:\n  sast:\n    rules:\n      - .semgrep/\n")
    assert sast.run() == 2
    assert semgrep_argv == []
    assert "does not exist" in sast.REPORT_MD.read_text()
