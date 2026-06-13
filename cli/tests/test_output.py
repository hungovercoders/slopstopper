"""Tests for the shared output formatters."""

from __future__ import annotations

from pathlib import Path

import pytest

from slopstopper import output


# ── reset the module-global between tests ────────────────────────


@pytest.fixture(autouse=True)
def _reset_quiet():
    output.set_quiet(False)
    yield
    output.set_quiet(False)


# ── basic formatters ─────────────────────────────────────────────


def test_running_prefixes_search_emoji(capsys):
    output.running("Analyzing things")
    assert capsys.readouterr().out == "🔍 Analyzing things\n"


def test_success_prefixes_check_mark(capsys):
    output.success("All good")
    assert capsys.readouterr().out == "✅ All good\n"


def test_warn_prefixes_warning(capsys):
    output.warn("Be careful")
    out = capsys.readouterr().out
    assert out.startswith("⚠️")
    assert "Be careful" in out


def test_info_prefixes_info(capsys):
    output.info("FYI")
    out = capsys.readouterr().out
    assert out.startswith("ℹ️")
    assert "FYI" in out


def test_error_prefixes_cross(capsys):
    output.error("Something failed")
    assert capsys.readouterr().out == "❌ Something failed\n"


def test_status_uses_caller_emoji(capsys):
    output.status("🔐", "Starting security scan")
    assert capsys.readouterr().out == "🔐 Starting security scan\n"


def test_separator_uses_box_drawing(capsys):
    output.separator()
    out = capsys.readouterr().out
    assert "━" in out
    assert len(out.rstrip("\n")) == output.SEPARATOR_WIDTH


def test_separator_respects_width(capsys):
    output.separator(width=10)
    assert capsys.readouterr().out.rstrip("\n") == "━" * 10


def test_section_emits_separator_title_separator(capsys):
    output.section("Findings", emoji="📊")
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert lines[0] == "━" * output.SEPARATOR_WIDTH
    assert lines[1] == "📊 Findings"
    assert lines[2] == "━" * output.SEPARATOR_WIDTH


def test_section_without_emoji(capsys):
    output.section("Plain title")
    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "Plain title"


def test_footer_lists_report_files(capsys):
    output.footer(Path(".ss/reports/foo"), ["foo-report.md", "foo-report.json"])
    out = capsys.readouterr().out
    assert ".ss/reports/foo/" in out
    assert "• foo-report.md" in out
    assert "• foo-report.json" in out


def test_blank_emits_empty_line(capsys):
    output.blank()
    assert capsys.readouterr().out == "\n"


# ── --quiet honouring ────────────────────────────────────────────


def test_quiet_suppresses_running(capsys):
    output.set_quiet(True)
    output.running("Should not appear")
    assert capsys.readouterr().out == ""


def test_quiet_suppresses_success(capsys):
    output.set_quiet(True)
    output.success("Hidden")
    assert capsys.readouterr().out == ""


def test_quiet_suppresses_warn_info_separator_section_footer(capsys):
    output.set_quiet(True)
    output.warn("w")
    output.info("i")
    output.separator()
    output.section("title", emoji="📊")
    output.footer(Path(".ss/reports/x"), ["a.md"])
    assert capsys.readouterr().out == ""


def test_quiet_does_not_suppress_error(capsys):
    """Errors are always emitted, even with --quiet."""
    output.set_quiet(True)
    output.error("Critical")
    assert "Critical" in capsys.readouterr().out


def test_quiet_via_emit_force_param_overrides(capsys):
    output.set_quiet(True)
    output._emit("forced", force=True)
    assert capsys.readouterr().out == "forced\n"


# ── integration: set_quiet round-trips ───────────────────────────


def test_set_quiet_toggles(capsys):
    output.set_quiet(True)
    assert output.QUIET is True
    output.set_quiet(False)
    assert output.QUIET is False
