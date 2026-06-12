"""Tests for the headers adapter registry and built-in adapters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopstopper import headers_adapters
from slopstopper.headers_adapters import cloudflare_adapter, json_adapter


# ── JSON adapter ──────────────────────────────────────────────────


def test_json_adapter_parses_basic_shape(tmp_path):
    payload = [
        {"for": "/foo", "values": {"Content-Security-Policy": "default-src 'self'"}},
        {"for": "/bar", "values": {"Cache-Control": "no-cache"}},
    ]
    path = tmp_path / "headers.json"
    path.write_text(json.dumps(payload))
    rules = json_adapter.parse(path)
    assert rules == [
        {"for": "/foo", "csp": "default-src 'self'"},
        {"for": "/bar", "csp": None},
    ]


def test_json_adapter_returns_empty_for_non_list(tmp_path):
    path = tmp_path / "headers.json"
    path.write_text(json.dumps({"oops": "object"}))
    assert json_adapter.parse(path) == []


def test_json_adapter_skips_malformed_entries(tmp_path):
    payload = [
        {"for": "/good", "values": {"Content-Security-Policy": "x"}},
        "string-entry",
        {"missing": "for"},
        {"for": 123, "values": {}},
        {"for": "/values-not-dict", "values": "x"},
    ]
    path = tmp_path / "headers.json"
    path.write_text(json.dumps(payload))
    rules = json_adapter.parse(path)
    assert rules == [{"for": "/good", "csp": "x"}]


# ── Cloudflare _headers adapter ────────────────────────────────────


def test_cloudflare_adapter_parses_two_blocks(tmp_path):
    path = tmp_path / "_headers"
    path.write_text(
        "/foo\n"
        "  Content-Security-Policy: default-src 'self'\n"
        "  Cache-Control: max-age=60\n"
        "\n"
        "/bar\n"
        "  Cache-Control: no-cache\n"
    )
    rules = cloudflare_adapter.parse(path)
    assert rules == [
        {"for": "/foo", "csp": "default-src 'self'"},
        {"for": "/bar", "csp": None},
    ]


def test_cloudflare_adapter_ignores_comments_and_blanks(tmp_path):
    path = tmp_path / "_headers"
    path.write_text(
        "# top comment\n"
        "\n"
        "/x\n"
        "  # indented comment lines are skipped\n"
        "  Content-Security-Policy: x\n"
    )
    assert cloudflare_adapter.parse(path) == [{"for": "/x", "csp": "x"}]


def test_cloudflare_adapter_handles_tab_indent(tmp_path):
    path = tmp_path / "_headers"
    path.write_text("/x\n\tContent-Security-Policy: tabbed\n")
    assert cloudflare_adapter.parse(path) == [{"for": "/x", "csp": "tabbed"}]


# ── Registry / dispatcher ─────────────────────────────────────────


def test_detect_format_json_for_json_extension(tmp_path):
    assert headers_adapters.detect_format(tmp_path / "x.json") == "json"


def test_detect_format_cloudflare_for_anything_else(tmp_path):
    assert headers_adapters.detect_format(tmp_path / "_headers") == "cloudflare-text"
    assert headers_adapters.detect_format(tmp_path / "x.toml") == "cloudflare-text"


def test_parse_auto_dispatches_by_extension(tmp_path):
    path = tmp_path / "h.json"
    path.write_text(json.dumps([{"for": "/", "values": {}}]))
    rules = headers_adapters.parse(path, "auto")
    assert rules == [{"for": "/", "csp": None}]


def test_parse_unknown_format_raises_key_error(tmp_path):
    with pytest.raises(KeyError):
        headers_adapters.parse(tmp_path / "x", "bogus-format")
