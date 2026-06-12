"""Tests for the hygiene:complexity check."""

from __future__ import annotations

from pathlib import Path

import pytest

from slopstopper.checks import complexity


# Sample CSV in lizard's shape: nloc,ccn,tokens,params,length,location,file,...
SAMPLE_CSV_LOW = (
    '5,2,42,1,7,"foo@10-14@./src/a.py","./src/a.py","foo","foo( x )",10,14\n'
    '8,3,80,2,12,"bar@20-31@./src/a.py","./src/a.py","bar","bar( x, y )",20,31\n'
)
SAMPLE_CSV_WITH_WARNING = (
    SAMPLE_CSV_LOW
    + '40,15,300,1,55,"complicated@40-94@./src/b.py","./src/b.py","complicated","complicated( x )",40,94\n'
)


def test_parse_csv_rows_extracts_numeric_fields():
    rows = complexity._parse_csv_rows(SAMPLE_CSV_LOW)
    assert len(rows) == 2
    assert rows[0][:5] == (5, 2, 42, 1, 7)
    assert rows[0][5] == "foo@10-14@./src/a.py"
    assert rows[0][6] == "./src/a.py"


def test_parse_csv_rows_skips_header_rows():
    csv_with_header = (
        "NLOC,CCN,token,PARAM,length,location,file\n"
        + SAMPLE_CSV_LOW
    )
    rows = complexity._parse_csv_rows(csv_with_header)
    assert len(rows) == 2


def test_parse_csv_rows_handles_missing_file_column():
    # Older fixtures may omit column 6 — fall back to location's @-segment.
    csv_no_file_col = '5,2,42,1,7,"foo@10-14@./src/a.py"\n'
    rows = complexity._parse_csv_rows(csv_no_file_col)
    assert rows[0][6] == "./src/a.py"


def test_parse_csv_rows_falls_back_for_colon_location():
    # Even older format: "path:line" instead of "func@start-end@./path".
    csv_colon = "5,2,42,1,7,src/a.py:10\n"
    rows = complexity._parse_csv_rows(csv_colon)
    assert rows[0][6] == "src/a.py"


def test_parse_csv_rows_returns_empty_on_empty_input():
    assert complexity._parse_csv_rows("") == []


def test_compute_summary_lines_empty_block():
    lines = complexity._compute_summary_lines([])
    assert "No functions analyzed." in lines
    assert any("Total NLOC" in line for line in lines)


def test_compute_summary_lines_aggregates_correctly():
    rows = complexity._parse_csv_rows(SAMPLE_CSV_LOW)
    lines = complexity._compute_summary_lines(rows)
    # Total NLOC = 5 + 8 = 13, fun_cnt = 2, files = {"./src/a.py"} → 1
    assert "13" in lines[2]
    assert "2 files" in lines[4] or "1 file" in lines[4]


def test_compute_summary_lines_counts_warnings():
    rows = complexity._parse_csv_rows(SAMPLE_CSV_WITH_WARNING)
    lines = complexity._compute_summary_lines(rows)
    # The third row has CCN=15 > 10 → warning_cnt = 1
    assert lines[2].split()[-1] == "1"


def test_format_summary_section_wraps_in_fence():
    section = complexity._format_summary_section(["line a", "line b"])
    assert section.startswith("```\n")
    assert section.endswith("```\n\n")
    assert "line a" in section


def test_format_summary_section_empty():
    assert complexity._format_summary_section([]) == ""


def test_format_high_complexity_section_clean():
    rows = complexity._parse_csv_rows(SAMPLE_CSV_LOW)
    section = complexity._format_high_complexity_section(rows)
    assert "✅" in section
    assert "No high-complexity items" in section


def test_format_high_complexity_section_with_warning():
    rows = complexity._parse_csv_rows(SAMPLE_CSV_WITH_WARNING)
    section = complexity._format_high_complexity_section(rows)
    assert "⚠️" in section
    assert "| 40 | 15 |" in section  # row table entry
    assert "complicated@40-94" in section


def test_build_md_report_contains_all_sections():
    rows = complexity._parse_csv_rows(SAMPLE_CSV_LOW)
    md = complexity._build_md_report(rows)
    assert "# Code Complexity Analysis Report" in md
    assert "## Summary" in md
    assert "## Guidelines" in md
    assert "## More Information" in md


def test_lizard_available_returns_false_when_subprocess_errors(monkeypatch):
    def fake_run(*args, **kwargs):
        raise OSError("nope")

    monkeypatch.setattr(complexity.subprocess, "run", fake_run)
    assert complexity._lizard_available() is False


def test_lizard_available_returns_true_on_success(monkeypatch):
    class FakeResult:
        returncode = 0

    monkeypatch.setattr(complexity.subprocess, "run", lambda *a, **k: FakeResult())
    assert complexity._lizard_available() is True


def test_run_returns_one_when_lizard_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(complexity, "_lizard_available", lambda: False)
    rc = complexity.run()
    assert rc == 1
    assert "lizard is not installed" in capsys.readouterr().out


def test_run_writes_csv_and_md_using_mocked_lizard(monkeypatch, isolated_cwd):
    monkeypatch.setattr(complexity, "_lizard_available", lambda: True)
    monkeypatch.setattr(complexity, "_run_lizard", lambda target_dir=".": SAMPLE_CSV_WITH_WARNING)
    rc = complexity.run()
    assert rc == 0
    assert complexity.REPORT_CSV.read_text() == SAMPLE_CSV_WITH_WARNING
    md = complexity.REPORT_MD.read_text()
    assert "⚠️ High Complexity Items" in md
    assert "complicated@40-94" in md


def test_run_reports_clean_when_no_warnings(monkeypatch, isolated_cwd, capsys):
    monkeypatch.setattr(complexity, "_lizard_available", lambda: True)
    monkeypatch.setattr(complexity, "_run_lizard", lambda target_dir=".": SAMPLE_CSV_LOW)
    rc = complexity.run()
    assert rc == 0
    out = capsys.readouterr().out
    assert "✅ No high-complexity items found" in out
