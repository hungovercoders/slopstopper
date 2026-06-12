"""Tests for the hygiene:csp-exceptions check."""

from __future__ import annotations

import json as _json
from pathlib import Path

from slopstopper.checks import csp_exceptions


HEADERS_JSON_TWO_EXCEPTIONS = _json.dumps([
    {
        "for": "/*",
        "values": {"Content-Security-Policy": "default-src 'self'; script-src 'self'"},
    },
    {
        "for": "/discuss",
        "values": {
            "Content-Security-Policy":
                "default-src 'self'; script-src 'self' https://giscus.app; "
                "frame-src https://giscus.app"
        },
    },
])


CSP_DOC_MATCHES = """# CSP Exceptions

Some preamble.

## Exceptions

### `/discuss`

- **Origin allowed:** `https://giscus.app`
- **Directives added:** `script-src https://giscus.app`, `frame-src https://giscus.app`
- **Loader SRI:** sha384-real-hash-here
- **Why:** giscus widget needs it
- **Approved by:** dataGriff
- **Data leaving site:** comments
- **Refresh policy:** check quarterly
"""


def test_extract_csp_origins_picks_only_external():
    origins = csp_exceptions._extract_csp_origins(
        "default-src 'self'; script-src 'self' https://giscus.app; frame-src https://giscus.app/"
    )
    assert origins == {"https://giscus.app"}


def test_extract_csp_origins_ignores_keywords():
    assert csp_exceptions._extract_csp_origins("default-src 'self' 'unsafe-inline'") == set()


def test_parse_exceptions_doc_picks_up_section(isolated_cwd):
    doc = isolated_cwd / "csp.md"
    doc.write_text(CSP_DOC_MATCHES)
    entries = csp_exceptions._parse_exceptions_doc(doc)
    assert set(entries) == {"/discuss"}
    e = entries["/discuss"]
    assert "https://giscus.app" in e["origins"]
    assert e["sri"] == "sha384-real-hash-here"
    assert csp_exceptions.REQUIRED_FIELDS.issubset(e["fields_seen"])


def test_parse_exceptions_doc_skips_baseline_slashstar(isolated_cwd):
    doc = isolated_cwd / "csp.md"
    doc.write_text(
        "## Exceptions\n\n### `/*`\n- **Origin allowed:** none\n\n### `/x`\n- **Origin allowed:** `https://a.com`\n"
    )
    entries = csp_exceptions._parse_exceptions_doc(doc)
    assert "/*" not in entries
    assert "/x" in entries


def test_parse_exceptions_doc_returns_empty_on_missing_file(isolated_cwd):
    assert csp_exceptions._parse_exceptions_doc(isolated_cwd / "no-such.md") == {}


def test_headers_exception_map_skips_baseline_and_no_csp():
    rules = [
        {"for": "/*", "csp": "default-src 'self' https://baseline.example"},
        {"for": "/none", "csp": None},
        {"for": "/keep", "csp": "default-src https://other.example"},
    ]
    assert csp_exceptions._headers_exception_map(rules) == {
        "/keep": {"https://other.example"},
    }


def test_sri_issues_warns_on_placeholder():
    issues = csp_exceptions._sri_issues("/x", "TODO-replace")
    assert len(issues) == 1
    assert issues[0]["severity"] == "warn"


def test_sri_issues_warns_on_empty():
    issues = csp_exceptions._sri_issues("/x", "")
    assert len(issues) == 1
    assert "no Loader SRI" in issues[0]["message"]


def test_sri_issues_silent_on_real_value():
    assert csp_exceptions._sri_issues("/x", "sha384-real") == []


def test_compare_flags_missing_doc_entry():
    rules = [
        {"for": "/x", "csp": "default-src https://example.com"},
    ]
    issues = csp_exceptions._compare(rules, {}, "test")
    assert any(i["severity"] == "error" and i["path"] == "/x" for i in issues)


def test_compare_flags_stale_doc_entry():
    issues = csp_exceptions._compare(
        rules=[],
        doc_entries={"/orphan": csp_exceptions._new_entry()},
        source_label="test",
    )
    assert any(i["severity"] == "error" and i["path"] == "/orphan" for i in issues)


def test_compare_clean_against_matching_doc(isolated_cwd):
    rules = [
        {"for": "/discuss", "csp": "script-src 'self' https://giscus.app"},
    ]
    doc = isolated_cwd / "csp.md"
    doc.write_text(CSP_DOC_MATCHES)
    doc_entries = csp_exceptions._parse_exceptions_doc(doc)
    issues = csp_exceptions._compare(rules, doc_entries, "test")
    # No errors; warnings only allowed if SRI is placeholder. SRI is real here.
    assert all(i["severity"] != "error" for i in issues)


def test_overall_status_fail_warn_pass():
    assert csp_exceptions._overall_status([{"severity": "error", "path": "/x", "message": "m"}]) == "❌ FAIL"
    assert csp_exceptions._overall_status([{"severity": "warn", "path": "/x", "message": "m"}]) == "⚠️ WARN"
    assert csp_exceptions._overall_status([]) == "✅ PASS"


def test_build_md_report_contains_status_and_source():
    md = csp_exceptions._build_md_report(
        [],
        {"doc_entries": 1, "headers_exceptions": 1, "source": "worker/headers.json", "format": "json"},
    )
    assert "✅ PASS" in md
    assert "worker/headers.json" in md
    assert "format: `json`" in md


def test_resolve_source_skip_when_unset(write_config):
    write_config("node_version: '20'\n")
    path, fmt, reason = csp_exceptions._resolve_source()
    assert path is None
    assert reason is not None


def test_resolve_source_skip_when_missing(write_config):
    write_config("headers:\n  source: missing/headers.json\n  format: json\n")
    path, fmt, reason = csp_exceptions._resolve_source()
    assert path == Path("missing/headers.json")
    assert "does not exist" in reason


def test_resolve_source_ok_when_present(isolated_cwd, write_config):
    headers = isolated_cwd / "headers.json"
    headers.write_text("[]")
    write_config("headers:\n  source: headers.json\n  format: json\n")
    path, fmt, reason = csp_exceptions._resolve_source()
    assert path == Path("headers.json")
    assert fmt == "json"
    assert reason is None


def _seed_csp_doc(text: str = CSP_DOC_MATCHES) -> None:
    target = Path("docs/security/CSP_EXCEPTIONS.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def test_run_skips_gracefully_when_no_source(isolated_cwd, capsys):
    rc = csp_exceptions.run()
    assert rc == 0
    assert "skipping" in capsys.readouterr().out


def test_run_returns_two_when_doc_missing(isolated_cwd, write_config, capsys):
    headers = isolated_cwd / "headers.json"
    headers.write_text(HEADERS_JSON_TWO_EXCEPTIONS)
    write_config("headers:\n  source: headers.json\n  format: json\n")
    rc = csp_exceptions.run()
    assert rc == 2
    assert "CSP_EXCEPTIONS.md not found" in capsys.readouterr().err


def test_run_returns_two_on_unknown_format(isolated_cwd, write_config, capsys):
    headers = isolated_cwd / "headers.json"
    headers.write_text("[]")
    write_config("headers:\n  source: headers.json\n  format: bogus\n")
    rc = csp_exceptions.run()
    assert rc == 2
    assert "Unknown headers.format" in capsys.readouterr().err


def test_run_returns_one_on_drift(isolated_cwd, write_config):
    headers = isolated_cwd / "headers.json"
    headers.write_text(HEADERS_JSON_TWO_EXCEPTIONS)
    write_config("headers:\n  source: headers.json\n  format: json\n")
    _seed_csp_doc("# CSP Exceptions\n\n## Exceptions\n\n(empty section)\n")
    rc = csp_exceptions.run()
    assert rc == 1
    report = _json.loads(csp_exceptions.REPORT_JSON.read_text())
    assert any(i["severity"] == "error" for i in report["issues"])


def test_run_clean_returns_zero(isolated_cwd, write_config):
    headers = isolated_cwd / "headers.json"
    headers.write_text(HEADERS_JSON_TWO_EXCEPTIONS)
    write_config("headers:\n  source: headers.json\n  format: json\n")
    _seed_csp_doc()
    rc = csp_exceptions.run()
    assert rc == 0
    report = _json.loads(csp_exceptions.REPORT_JSON.read_text())
    assert all(i["severity"] != "error" for i in report["issues"])
