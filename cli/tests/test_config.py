"""Smoke tests for the .slopstopper.yml subset parser."""

from __future__ import annotations

from slopstopper import config


def test_missing_file_returns_default(isolated_cwd):
    assert config.get("hygiene.docs_size.max_files", 25) == 25
    assert config.get("anything.at.all") is None


def test_top_level_scalar(write_config):
    write_config("answer: '42'\n")
    assert config.get("answer") == "42"


def test_nested_dot_path(write_config):
    write_config(
        "hygiene:\n"
        "  docs_size:\n"
        "    max_files: 10\n"
    )
    assert config.get("hygiene.docs_size.max_files") == "10"
    assert config.get("hygiene.docs_size.missing", "fallback") == "fallback"


def test_inline_list(write_config):
    write_config("workflows:\n  disabled: [foo, bar]\n")
    assert config.get("workflows.disabled") == ["foo", "bar"]


def test_block_list(write_config):
    write_config(
        "workflows:\n"
        "  disabled:\n"
        "    - foo\n"
        "    - bar\n"
    )
    assert config.get("workflows.disabled") == ["foo", "bar"]


def test_null_value_returns_default(write_config):
    write_config("headers:\n  source: null\n")
    assert config.get("headers.source", "fallback") == "fallback"


def test_comment_stripping(write_config):
    write_config("answer: '42'  # inline comment\n# whole-line comment\n")
    assert config.get("answer") == "42"
