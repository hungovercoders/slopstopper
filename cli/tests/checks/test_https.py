"""Tests for the security:https check."""

from __future__ import annotations

import json
import urllib.error

import pytest

from slopstopper.checks import https

SITE = "https://example.com"
HSTS = {"Strict-Transport-Security": "max-age=15552000"}
REDIRECT = (301, {"Location": "https://example.com/"})


def _answers(monkeypatch, *, secure=(200, HSTS), plain=REDIRECT):
    """Fake the two requests. Either answer may be an exception to raise."""
    asked: list[str] = []

    def probe(url: str):
        asked.append(url)
        answer = secure if url.startswith("https://") else plain
        if isinstance(answer, BaseException):
            raise answer
        return answer

    monkeypatch.setattr(https, "_probe", probe)
    return asked


@pytest.fixture(autouse=True)
def _in_tmp(isolated_cwd, monkeypatch):
    monkeypatch.delenv("HTTPS_TEST_URL", raising=False)


# ── arg / config plumbing ────────────────────────────────────────


def test_parse_args_defaults():
    parsed = https._parse_args(None)
    assert parsed.url is None
    assert parsed.no_require_hsts is False


def test_resolve_url_prefers_flag(monkeypatch):
    monkeypatch.setenv("HTTPS_TEST_URL", "https://from-env")
    assert https._resolve_url("https://from-flag") == "https://from-flag"
    assert https._resolve_url(None) == "https://from-env"


def test_no_url_cannot_run():
    assert https.run([]) == 2


def test_a_file_url_cannot_run():
    assert https.run(["file:///etc/passwd"]) == 2


# ── the pass ─────────────────────────────────────────────────────


def test_redirect_and_hsts_pass(monkeypatch):
    asked = _answers(monkeypatch)
    assert https.run([SITE]) == 0
    assert asked == ["https://example.com/", "http://example.com/"]
    report = json.loads(https.REPORT_JSON.read_text())
    assert report["status"] == "pass"
    assert report["redirect"] == {
        "url": "http://example.com/", "status": 301, "location": "https://example.com/",
    }


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_every_redirect_status_counts(monkeypatch, status):
    _answers(monkeypatch, plain=(status, {"location": "https://EXAMPLE.com/path"}))
    assert https.run([SITE]) == 0


def test_a_path_on_the_target_is_not_what_is_asked(monkeypatch):
    asked = _answers(monkeypatch)
    assert https.run([SITE + "/docs/page.html"]) == 0
    assert asked == ["https://example.com/", "http://example.com/"]


# ── the redirect ─────────────────────────────────────────────────


def test_a_page_over_plain_http_fails_and_names_the_fix(monkeypatch):
    _answers(monkeypatch, plain=(200, {}))
    assert https.run([SITE]) == 1
    report = https.REPORT_MD.read_text()
    assert "- ❌ `http://example.com/` answered HTTP 200 with no redirect to https" in report
    assert "Always Use HTTPS" in report


def test_a_404_over_plain_http_fails(monkeypatch):
    _answers(monkeypatch, plain=(404, {}))
    assert https.run([SITE]) == 1


def test_a_redirect_that_stays_on_http_fails(monkeypatch):
    _answers(monkeypatch, plain=(301, {"Location": "http://example.com/home"}))
    assert https.run([SITE]) == 1
    assert "which is not https" in https.REPORT_MD.read_text()


def test_a_relative_redirect_stays_on_http_and_fails(monkeypatch):
    _answers(monkeypatch, plain=(302, {"Location": "/home"}))
    assert https.run([SITE]) == 1


def test_a_redirect_to_another_host_fails(monkeypatch):
    _answers(monkeypatch, plain=(301, {"Location": "https://www.example.com/"}))
    assert https.run([SITE]) == 1
    assert "another host, `www.example.com`" in https.REPORT_MD.read_text()


def test_nothing_on_port_80_is_a_pass_with_a_note(monkeypatch):
    _answers(monkeypatch, plain=urllib.error.URLError("Connection refused"))
    assert https.run([SITE]) == 0
    assert "no plain-HTTP page to redirect" in https.REPORT_MD.read_text()


def test_a_custom_port_is_audited_for_hsts_only(monkeypatch):
    asked = _answers(monkeypatch)
    assert https.run(["https://example.com:8443"]) == 0
    assert asked == ["https://example.com:8443/"]
    assert "custom port" in https.REPORT_MD.read_text()


# ── HSTS ─────────────────────────────────────────────────────────


def test_missing_hsts_fails_and_says_where_the_header_goes(monkeypatch):
    _answers(monkeypatch, secure=(200, {}))
    assert https.run([SITE]) == 1
    report = https.REPORT_MD.read_text()
    assert "- ❌ `Strict-Transport-Security` is missing" in report
    assert "_headers" in report and "worker/headers.json" in report


@pytest.mark.parametrize("value", ["max-age=0", "includeSubDomains"])
def test_an_hsts_header_that_does_nothing_fails(monkeypatch, value):
    _answers(monkeypatch, secure=(200, {"strict-transport-security": value}))
    assert https.run([SITE]) == 1


def test_the_flag_turns_the_hsts_demand_off(monkeypatch):
    _answers(monkeypatch, secure=(200, {}))
    assert https.run([SITE, "--no-require-hsts"]) == 0
    assert "not required" in https.REPORT_MD.read_text()


def test_the_config_knob_turns_the_hsts_demand_off(monkeypatch, write_config):
    write_config("security:\n  https:\n    require_hsts: false\n")
    _answers(monkeypatch, secure=(200, {}))
    assert https.run([SITE]) == 0


def test_hsts_is_read_from_an_error_response_too(monkeypatch):
    _answers(monkeypatch, secure=(403, HSTS))
    assert https.run([SITE]) == 0


# ── skips and could-not-run ──────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    ["http://localhost:8080", "https://localhost", "http://127.0.0.1:3000", "http://[::1]:8080",
     "http://app.localhost", "http://example.com"],
)
def test_a_local_or_plain_http_target_is_skipped(monkeypatch, url):
    asked = _answers(monkeypatch)
    assert https.run([url]) == 0
    assert asked == []
    assert "SKIPPED" in https.REPORT_MD.read_text()


@pytest.mark.parametrize(
    "error", [urllib.error.URLError("Name or service not known"), TimeoutError("timed out")]
)
def test_an_unreachable_https_host_cannot_run(monkeypatch, error):
    _answers(monkeypatch, secure=error)
    assert https.run([SITE]) == 2
    assert not https.REPORT_MD.exists()
