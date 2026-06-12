"""Tests for the hygiene:entry-files check."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopstopper.checks import entry_files


def _seed_entry_files(root: Path, contents: dict[str, str]) -> None:
    for name in entry_files.ENTRY_FILES:
        body = contents.get(name, f"placeholder for {name}\n")
        (root / name).write_text(body)


def test_count_words_strips_whitespace(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("one two   three\nfour\tfive\n")
    assert entry_files._count_words(f) == 5


def test_measure_returns_none_for_missing_file(isolated_cwd):
    assert entry_files._measure("nope.md", 1500) is None


def test_measure_returns_dict_for_present_file(isolated_cwd):
    (isolated_cwd / "AGENTS.md").write_text("alpha beta gamma\n")
    m = entry_files._measure("AGENTS.md", 1500)
    assert m == {
        "file": "AGENTS.md",
        "words": 3,
        "budget": 1500,
        "over_budget": False,
        "headroom": 1497,
    }


def test_measure_flags_over_budget(isolated_cwd):
    (isolated_cwd / "README.md").write_text("word " * 100)
    m = entry_files._measure("README.md", 50)
    assert m["over_budget"] is True
    assert m["words"] == 100
    assert m["headroom"] == -50


def test_measure_all_partitions_present_and_missing(isolated_cwd):
    (isolated_cwd / "README.md").write_text("hello world\n")
    (isolated_cwd / "AGENTS.md").write_text("a b c d e\n")
    measurements, missing = entry_files._measure_all(1500)
    assert [m["file"] for m in measurements] == ["README.md", "AGENTS.md"]
    assert missing == ["CLAUDE.md"]


def test_load_max_words_default(isolated_cwd):
    assert entry_files._load_max_words() == entry_files.DEFAULT_MAX_WORDS


def test_load_max_words_override(write_config):
    write_config("hygiene:\n  entry_files:\n    max_words: 800\n")
    assert entry_files._load_max_words() == 800


def test_load_max_words_garbage_falls_back(write_config):
    write_config("hygiene:\n  entry_files:\n    max_words: bananas\n")
    assert entry_files._load_max_words() == entry_files.DEFAULT_MAX_WORDS


def test_status_line_clean():
    assert "✅" in entry_files._status_line(True, 1500)
    assert "within budget" in entry_files._status_line(True, 1500)


def test_status_line_alert_uses_budget():
    line = entry_files._status_line(False, 1500)
    assert "❌" in line
    assert "1,500-word" in line


def test_build_md_report_includes_rows_and_status():
    measurements = [
        {"file": "README.md", "words": 100, "budget": 1500, "over_budget": False, "headroom": 1400},
        {"file": "AGENTS.md", "words": 1600, "budget": 1500, "over_budget": True, "headroom": -100},
    ]
    md = entry_files._build_md_report(
        measurements, "2026-06-12 00:00:00 UTC", "❌ One or more entry files exceed the 1,500-word budget."
    )
    assert "📏 Entry-File Size Report" in md
    assert "`README.md`" in md
    assert "✅ ok" in md
    assert "❌ over" in md
    assert "+1400" in md
    assert "-100" in md


def test_build_json_report_round_trips():
    measurements = [
        {"file": "README.md", "words": 100, "budget": 1500, "over_budget": False, "headroom": 1400},
    ]
    payload_str = entry_files._build_json_report(measurements, "2026-06-12 00:00:00 UTC", 1500, True)
    payload = json.loads(payload_str)
    assert payload["generated_at"] == "2026-06-12 00:00:00 UTC"
    assert payload["budget_words"] == 1500
    assert payload["measurements"] == measurements
    assert payload["clean"] is True
    assert payload["violation_count"] == 0


def test_build_json_report_counts_violations():
    measurements = [
        {"file": "AGENTS.md", "words": 2000, "budget": 1500, "over_budget": True, "headroom": -500},
        {"file": "CLAUDE.md", "words": 100, "budget": 1500, "over_budget": False, "headroom": 1400},
    ]
    payload = json.loads(
        entry_files._build_json_report(measurements, "t", 1500, False)
    )
    assert payload["violation_count"] == 1
    assert payload["clean"] is False


def test_run_clean_returns_zero_and_writes_both_reports(isolated_cwd, capsys):
    _seed_entry_files(isolated_cwd, {})  # tiny placeholders for all three
    rc = entry_files.run()
    assert rc == 0
    assert entry_files.REPORT_MD.exists()
    assert entry_files.REPORT_JSON.exists()
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    assert payload["clean"] is True
    assert payload["violation_count"] == 0


def test_run_returns_one_when_over_budget(isolated_cwd, write_config, capsys):
    write_config("hygiene:\n  entry_files:\n    max_words: 2\n")
    _seed_entry_files(isolated_cwd, {"README.md": "one two three four five\n"})
    rc = entry_files.run()
    assert rc == 1
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    assert payload["clean"] is False
    assert payload["violation_count"] >= 1


def test_run_returns_two_when_entry_file_missing(isolated_cwd, capsys):
    (isolated_cwd / "README.md").write_text("present\n")
    # AGENTS.md and CLAUDE.md deliberately omitted
    rc = entry_files.run()
    assert rc == 2
    err = capsys.readouterr().out
    assert "AGENTS.md" in err or "CLAUDE.md" in err
