"""Tests for the DAST gate logic (cli/slopstopper/dast_gate.py)."""

from __future__ import annotations

import json

from slopstopper import dast_gate


# ── documented_exception_paths ───────────────────────────────────


def test_documented_exception_paths_extracts_only_section_headings(tmp_path):
    doc = tmp_path / "CSP_EXCEPTIONS.md"
    doc.write_text(
        "# CSP exceptions\n\n"
        "Intro prose\n\n"
        "## Process\n\n"
        "### `/this-should-not-count`\n\n"
        "## Exceptions\n\n"
        "### `/feedback.html`\n\n"
        "rationale...\n\n"
        "### `/blog/*`\n\n"
        "## Other section\n\n"
        "### `/also-skip`\n"
    )
    assert dast_gate.documented_exception_paths(doc) == {"/feedback.html", "/blog/*"}


def test_documented_exception_paths_returns_empty_when_doc_missing(tmp_path):
    assert dast_gate.documented_exception_paths(tmp_path / "missing.md") == set()


# ── ignored_plugin_ids ───────────────────────────────────────────


def test_ignored_plugin_ids_parses_tsv(tmp_path):
    rules = tmp_path / "rules.tsv"
    rules.write_text(
        "# header comment\n"
        "10063\tIGNORE\tinformational rule\n"
        "10038\tWARN\tdo not skip warns\n"
        "90003\tIGNORE\n"
        "\n"
    )
    assert dast_gate.ignored_plugin_ids(rules) == {"10063", "90003"}


def test_ignored_plugin_ids_returns_empty_when_missing(tmp_path):
    assert dast_gate.ignored_plugin_ids(tmp_path / "nope.tsv") == set()


# ── is_csp_alert ─────────────────────────────────────────────────


def test_is_csp_alert_matches_pluginid():
    assert dast_gate.is_csp_alert({"pluginid": "10055"}) is True
    assert dast_gate.is_csp_alert({"pluginid": "99999"}) is False


def test_is_csp_alert_matches_name_hint():
    assert dast_gate.is_csp_alert({"alert": "Content Security Policy header missing"}) is True
    assert dast_gate.is_csp_alert({"name": "csp wildcard directive"}) is True
    assert dast_gate.is_csp_alert({"alert": "X-XSS-Protection header missing"}) is False


# ── _match_exception_path ────────────────────────────────────────


def test_match_exception_path_exact():
    assert dast_gate._match_exception_path("/feedback.html", {"/feedback.html"}) == "/feedback.html"


def test_match_exception_path_glob():
    assert dast_gate._match_exception_path("/blog/post-1", {"/blog/*"}) == "/blog/*"


def test_match_exception_path_no_match():
    assert dast_gate._match_exception_path("/admin", {"/blog/*", "/feedback.html"}) is None


# ── classify_alerts ──────────────────────────────────────────────


def _alert(riskcode=2, pluginid="10055", alert_name="CSP", uri="https://example.com/feedback.html"):
    return {
        "pluginid": pluginid,
        "riskcode": str(riskcode),
        "alert": alert_name,
        "instances": [{"uri": uri}],
    }


def test_classify_swallows_documented_csp_on_documented_path():
    zap = {"site": [{"alerts": [_alert(riskcode=2, pluginid="10055", uri="https://example.com/feedback.html")]}]}
    blocking, swallowed = dast_gate.classify_alerts(zap, {"/feedback.html"}, set())
    assert blocking == 0
    assert len(swallowed) == 1
    assert swallowed[0]["path"] == "/feedback.html"
    assert swallowed[0]["source"] == "docs/security/CSP_EXCEPTIONS.md"


def test_classify_does_not_swallow_high_risk_csp_even_on_exception_path():
    zap = {"site": [{"alerts": [_alert(riskcode=3, pluginid="10055", uri="https://example.com/feedback.html")]}]}
    blocking, swallowed = dast_gate.classify_alerts(zap, {"/feedback.html"}, set())
    assert blocking == 1
    assert swallowed == []


def test_classify_blocks_csp_on_undocumented_path():
    zap = {"site": [{"alerts": [_alert(riskcode=2, pluginid="10055", uri="https://example.com/admin")]}]}
    blocking, swallowed = dast_gate.classify_alerts(zap, {"/feedback.html"}, set())
    assert blocking == 1
    assert swallowed == []


def test_classify_blocks_non_csp_on_exception_path():
    # Some other Medium finding on a CSP-excepted path still blocks
    zap = {"site": [{"alerts": [_alert(riskcode=2, pluginid="99999", alert_name="XSS")]}]}
    blocking, swallowed = dast_gate.classify_alerts(zap, {"/feedback.html"}, set())
    assert blocking == 1
    assert swallowed == []


def test_classify_swallows_via_zap_rules_ignore():
    """An IGNORE-listed plugin id is swallowed regardless of path or alert class."""
    zap = {"site": [{"alerts": [_alert(riskcode=2, pluginid="90003", alert_name="SRI")]}]}
    blocking, swallowed = dast_gate.classify_alerts(zap, set(), {"90003"})
    assert blocking == 0
    assert len(swallowed) == 1
    assert swallowed[0]["source"] == ".zap/rules.tsv"


def test_classify_ignores_low_risk_alerts():
    zap = {"site": [{"alerts": [_alert(riskcode=1, pluginid="10055")]}]}
    blocking, swallowed = dast_gate.classify_alerts(zap, set(), set())
    assert blocking == 0
    assert swallowed == []


def test_classify_handles_alert_without_instances_array():
    alert = {"pluginid": "99999", "riskcode": "2", "url": "https://x.com/a", "alert": "XSS"}
    zap = {"site": [{"alerts": [alert]}]}
    blocking, _ = dast_gate.classify_alerts(zap, set(), set())
    assert blocking == 1


# ── write_gate_report ────────────────────────────────────────────


def test_write_gate_report_writes_json(tmp_path, monkeypatch):
    gate_path = tmp_path / "dast" / "dast-gate.json"
    monkeypatch.setattr(dast_gate, "GATE_REPORT", gate_path)
    dast_gate.write_gate_report(2, [{"path": "/x", "pluginid": "10055", "alert": "CSP", "riskcode": 2}])
    payload = json.loads(gate_path.read_text())
    assert payload["blocking"] == 2
    assert len(payload["swallowed"]) == 1


# ── swallowed_preamble_md ────────────────────────────────────────


def test_swallowed_preamble_md_empty_when_no_swallowed():
    assert dast_gate.swallowed_preamble_md([]) == ""


def test_swallowed_preamble_md_renders_each_finding():
    md = dast_gate.swallowed_preamble_md([
        {"path": "/feedback.html", "pluginid": "10055", "alert": "CSP wildcard", "riskcode": 2},
    ])
    assert "🛡 Documented CSP exceptions" in md
    assert "/feedback.html" in md
    assert "pluginid `10055`" in md
    assert "CSP wildcard" in md


# ── format_summary_text ──────────────────────────────────────────


def test_format_summary_text_clean():
    out = dast_gate.format_summary_text(0, [])
    assert "✅ No blocking findings." in out


def test_format_summary_text_with_blocking():
    out = dast_gate.format_summary_text(3, [])
    assert "❌ 3 blocking finding(s)" in out


def test_format_summary_text_lists_swallowed():
    out = dast_gate.format_summary_text(0, [
        {"path": "/feedback.html", "pluginid": "10055", "alert": "CSP", "riskcode": 2},
    ])
    assert "🛡 /feedback.html" in out
