"""Tests for the hygiene:entry-files check."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopstopper.checks import entry_files


MAP_POINTER = (
    "> 🗺️ **Documentation map.** "
    "[`docs/index.md`](./docs/index.md) is the single index of all project documentation. "
    "This file is intentionally thin — it points at the map.\n"
)


def _seed_entry_files(root: Path, contents: dict[str, str]) -> None:
    """Seed the trio with sensible defaults that satisfy the pointer rule."""
    defaults = {
        "README.md": MAP_POINTER,
        "AGENTS.md": MAP_POINTER,
        "CLAUDE.md": "Defer to [AGENTS.md](./AGENTS.md).\n\n@AGENTS.md\n",
    }
    for name in entry_files.ENTRY_FILES:
        body = contents.get(name, defaults[name])
        (root / name).write_text(body)


def _seed_map_file(root: Path) -> None:
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "index.md").write_text("# Documentation Index\n")


def test_count_words_strips_whitespace(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("one two   three\nfour\tfive\n")
    assert entry_files._count_words(f) == 5


def test_measure_returns_none_for_missing_file(isolated_cwd):
    assert entry_files._measure("nope.md", 1500, Path("docs/index.md"), True) is None


def test_measure_returns_dict_for_present_file(isolated_cwd):
    (isolated_cwd / "AGENTS.md").write_text(f"alpha beta gamma\n{MAP_POINTER}")
    _seed_map_file(isolated_cwd)
    m = entry_files._measure("AGENTS.md", 1500, Path("docs/index.md"), True)
    assert m is not None
    assert m["file"] == "AGENTS.md"
    assert m["budget"] == 1500
    assert m["over_budget"] is False
    assert m["pointer_ok"] is True


def test_measure_flags_over_budget(isolated_cwd):
    (isolated_cwd / "README.md").write_text("word " * 100)
    m = entry_files._measure("README.md", 50, Path("docs/index.md"), False)
    assert m["over_budget"] is True
    assert m["words"] == 100
    assert m["headroom"] == -50


def test_measure_all_partitions_present_and_missing(isolated_cwd):
    (isolated_cwd / "README.md").write_text("hello world\n")
    (isolated_cwd / "AGENTS.md").write_text("a b c d e\n")
    measurements, missing = entry_files._measure_all(1500, Path("docs/index.md"), False)
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


def test_load_require_map_pointer_default_true(isolated_cwd):
    assert entry_files._load_require_map_pointer() is True


def test_load_require_map_pointer_override(write_config):
    write_config("hygiene:\n  entry_files:\n    require_map_pointer: false\n")
    assert entry_files._load_require_map_pointer() is False


def test_load_map_path_default(isolated_cwd):
    assert entry_files._load_map_path() == "docs/index.md"


def test_load_map_path_override(write_config):
    write_config("hygiene:\n  entry_files:\n    map_path: docs/MAP.md\n")
    assert entry_files._load_map_path() == "docs/MAP.md"


def test_status_line_clean():
    assert "✅" in entry_files._status_line(True, 1500)
    assert "within budget" in entry_files._status_line(True, 1500)


def test_status_line_alert_uses_budget():
    line = entry_files._status_line(False, 1500)
    assert "❌" in line
    assert "1,500-word" in line


def test_build_md_report_includes_rows_and_status():
    measurements = [
        {
            "file": "README.md", "words": 100, "budget": 1500,
            "over_budget": False, "headroom": 1400,
            "pointer_ok": True, "pointer_violation": None,
        },
        {
            "file": "AGENTS.md", "words": 1600, "budget": 1500,
            "over_budget": True, "headroom": -100,
            "pointer_ok": True, "pointer_violation": None,
        },
    ]
    md = entry_files._build_md_report(
        measurements, "2026-06-12 00:00:00 UTC",
        "❌ One or more entry files exceed the 1,500-word budget or are missing the Map Pattern pointer.",
        "docs/index.md", False,
    )
    assert "📏 Entry-File Size + Map Pattern Report" in md
    assert "`README.md`" in md
    assert "✅ ok" in md
    assert "❌ over" in md
    assert "+1400" in md
    assert "-100" in md


def test_build_md_report_emits_paste_ready_pointer_snippet():
    measurements = [
        {
            "file": "AGENTS.md", "words": 100, "budget": 1500,
            "over_budget": False, "headroom": 1400,
            "pointer_ok": False, "pointer_violation": "missing_map_pointer",
        },
    ]
    md = entry_files._build_md_report(
        measurements, "t", "❌", "docs/index.md", False,
    )
    assert "Paste this near the top of `AGENTS.md`" in md
    assert "[`docs/index.md`](./docs/index.md)" in md


def test_build_md_report_emits_claude_thin_pointer_snippet():
    measurements = [
        {
            "file": "CLAUDE.md", "words": 50, "budget": 1500,
            "over_budget": False, "headroom": 1450,
            "pointer_ok": False, "pointer_violation": "claude_not_thin_pointer",
        },
    ]
    md = entry_files._build_md_report(
        measurements, "t", "❌", "docs/index.md", False,
    )
    assert "thin pointer" in md.lower()
    assert "@AGENTS.md" in md
    assert "[`AGENTS.md`](./AGENTS.md)" in md


def test_build_md_report_calls_out_missing_map_file():
    md = entry_files._build_md_report(
        [], "t", "❌", "docs/index.md", True,
    )
    assert "`docs/index.md` not found" in md
    assert "does not exist" in md


def test_build_json_report_round_trips():
    measurements = [
        {
            "file": "README.md", "words": 100, "budget": 1500,
            "over_budget": False, "headroom": 1400,
            "pointer_ok": True, "pointer_violation": None,
        },
    ]
    payload_str = entry_files._build_json_report(
        measurements, "2026-06-12 00:00:00 UTC", 1500, "docs/index.md", False, True, True
    )
    payload = json.loads(payload_str)
    assert payload["generated_at"] == "2026-06-12 00:00:00 UTC"
    assert payload["budget_words"] == 1500
    assert payload["map_path"] == "docs/index.md"
    assert payload["map_file_present"] is True
    assert payload["measurements"] == measurements
    assert payload["clean"] is True
    assert payload["violation_count"] == 0


def test_build_json_report_counts_violations():
    measurements = [
        {
            "file": "AGENTS.md", "words": 2000, "budget": 1500,
            "over_budget": True, "headroom": -500,
            "pointer_ok": False, "pointer_violation": "missing_map_pointer",
        },
        {
            "file": "CLAUDE.md", "words": 100, "budget": 1500,
            "over_budget": False, "headroom": 1400,
            "pointer_ok": True, "pointer_violation": None,
        },
    ]
    payload = json.loads(
        entry_files._build_json_report(
            measurements, "t", 1500, "docs/index.md", True, True, False
        )
    )
    # AGENTS counts once (over_budget OR pointer fail) + missing map file = 2
    assert payload["violation_count"] == 2
    assert payload["clean"] is False
    assert payload["map_file_present"] is False


def test_run_clean_returns_zero_and_writes_both_reports(isolated_cwd, capsys):
    _seed_entry_files(isolated_cwd, {})
    _seed_map_file(isolated_cwd)
    rc = entry_files.run()
    assert rc == 0
    assert entry_files.REPORT_MD.exists()
    assert entry_files.REPORT_JSON.exists()
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    assert payload["clean"] is True
    assert payload["violation_count"] == 0


def test_run_returns_one_when_over_budget(isolated_cwd, write_config, capsys):
    write_config("hygiene:\n  entry_files:\n    max_words: 2\n    require_map_pointer: false\n")
    _seed_entry_files(isolated_cwd, {"README.md": "one two three four five\n"})
    rc = entry_files.run()
    assert rc == 1
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    assert payload["clean"] is False
    assert payload["violation_count"] >= 1


def test_run_returns_one_when_pointer_missing(isolated_cwd, capsys):
    _seed_entry_files(isolated_cwd, {
        "README.md": "no pointer here\n",
        "AGENTS.md": MAP_POINTER,
        "CLAUDE.md": "@AGENTS.md\n",
    })
    _seed_map_file(isolated_cwd)
    rc = entry_files.run()
    assert rc == 1
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    flags = {m["file"]: m["pointer_ok"] for m in payload["measurements"]}
    assert flags["README.md"] is False
    assert flags["AGENTS.md"] is True
    assert flags["CLAUDE.md"] is True


def test_run_returns_one_when_claude_missing_agents_pointer(isolated_cwd, capsys):
    _seed_entry_files(isolated_cwd, {
        "README.md": MAP_POINTER,
        "AGENTS.md": MAP_POINTER,
        "CLAUDE.md": "Some unrelated content with no reference to agents.\n",
    })
    _seed_map_file(isolated_cwd)
    rc = entry_files.run()
    assert rc == 1
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    flags = {m["file"]: m["pointer_violation"] for m in payload["measurements"]}
    assert flags["CLAUDE.md"] == "claude_not_thin_pointer"


def test_run_returns_one_when_map_file_missing(isolated_cwd, capsys):
    _seed_entry_files(isolated_cwd, {})
    # Note: no _seed_map_file call
    rc = entry_files.run()
    assert rc == 1
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    assert payload["map_file_present"] is False


def test_run_respects_disabled_pointer_rule(isolated_cwd, write_config, capsys):
    write_config("hygiene:\n  entry_files:\n    require_map_pointer: false\n")
    _seed_entry_files(isolated_cwd, {
        "README.md": "no pointer\n",
        "AGENTS.md": "no pointer\n",
        "CLAUDE.md": "no pointer\n",
    })
    # Map file deliberately missing
    rc = entry_files.run()
    assert rc == 0
    payload = json.loads(entry_files.REPORT_JSON.read_text())
    assert payload["clean"] is True


def test_run_accepts_anchored_map_link(isolated_cwd, capsys):
    _seed_entry_files(isolated_cwd, {
        "README.md": "[map](./docs/index.md#the-map-pattern)\n",
        "AGENTS.md": "[map](docs/index.md)\n",
        "CLAUDE.md": "@AGENTS.md\n",
    })
    _seed_map_file(isolated_cwd)
    rc = entry_files.run()
    assert rc == 0


def test_run_returns_two_when_entry_file_missing(isolated_cwd, capsys):
    (isolated_cwd / "README.md").write_text("present\n")
    # AGENTS.md and CLAUDE.md deliberately omitted
    rc = entry_files.run()
    assert rc == 2
    err = capsys.readouterr().out
    assert "AGENTS.md" in err or "CLAUDE.md" in err
