"""Tests for the helpers shared across checks: _http, _report, _playwright.

These used to be copied into each check module (eight SSRF guards, seven
fetches, nine timestamps in three formats). Now there is one of each,
and this is where its behaviour is pinned.
"""

from __future__ import annotations

import io
import urllib.error
from pathlib import Path

import pytest

from slopstopper.checks import _http, _playwright, _report


# ── _http ────────────────────────────────────────────────────────


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "gopher://x", "javascript:alert(1)"])
def test_require_safe_url_refuses_non_http(url):
    with pytest.raises(ValueError, match="API health check refuses scheme"):
        _http.require_safe_url(url, "API health check")


@pytest.mark.parametrize("url", ["http://example.com", "HTTPS://example.com/x"])
def test_require_safe_url_allows_http_and_https(url):
    _http.require_safe_url(url)


def test_open_url_guards_before_opening(monkeypatch):
    """The guard must run before urlopen — that is the whole point."""
    called = []
    monkeypatch.setattr(_http.urllib.request, "urlopen", lambda req, timeout: called.append(req))
    with pytest.raises(ValueError):
        _http.open_url("file:///etc/passwd", "ua")
    assert called == []


class _FakeResponse:
    def __init__(self, status=200, headers=None, body=b""):
        self.status = status
        self.headers = headers or {}
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_open_url_sends_user_agent_method_and_extra_headers(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["method"] = req.get_method()
        seen["headers"] = dict(req.header_items())
        seen["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(_http.urllib.request, "urlopen", fake_urlopen)
    with _http.open_url("https://x.example/p", "SlopStopper-Test/1.0", method="HEAD",
                        headers={"Origin": "https://app.example"}, timeout=7):
        pass
    assert seen["url"] == "https://x.example/p"
    assert seen["method"] == "HEAD"
    assert seen["headers"]["User-agent"] == "SlopStopper-Test/1.0"
    assert seen["headers"]["Origin"] == "https://app.example"
    assert seen["timeout"] == 7


def test_fetch_text_returns_status_type_and_decoded_body(monkeypatch):
    monkeypatch.setattr(
        _http.urllib.request, "urlopen",
        lambda req, timeout: _FakeResponse(200, {"Content-Type": "text/html"}, "héllo".encode()),
    )
    assert _http.fetch_text("https://x.example", "ua") == (200, "text/html", "héllo")


def test_head_ok_maps_statuses_and_errors(monkeypatch):
    monkeypatch.setattr(_http.urllib.request, "urlopen", lambda req, timeout: _FakeResponse(204))
    assert _http.head_ok("https://x.example", "ua") == (True, "HTTP 204")

    monkeypatch.setattr(_http.urllib.request, "urlopen", lambda req, timeout: _FakeResponse(404))
    assert _http.head_ok("https://x.example", "ua") == (False, "HTTP 404")

    def raise_http(req, timeout):
        raise urllib.error.HTTPError("https://x", 500, "boom", {}, io.BytesIO())

    monkeypatch.setattr(_http.urllib.request, "urlopen", raise_http)
    assert _http.head_ok("https://x.example", "ua") == (False, "HTTP 500")

    def raise_url(req, timeout):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr(_http.urllib.request, "urlopen", raise_url)
    ok, detail = _http.head_ok("https://x.example", "ua")
    assert ok is False and detail.startswith("URLError")

    # A refused scheme is a detail, not an exception, for a HEAD probe.
    assert _http.head_ok("file:///etc/passwd", "ua")[0] is False


@pytest.mark.parametrize(
    "url,base_path,path,expected",
    [
        ("https://api.example.com", "", "/health", "https://api.example.com/health"),
        ("https://api.example.com/", "", "/health", "https://api.example.com/health"),
        ("https://api.example.com", "/api/v1", "/health", "https://api.example.com/api/v1/health"),
        ("https://api.example.com", "/api/v1/", "/health", "https://api.example.com/api/v1/health"),
        ("https://api.example.com", "", "health", "https://api.example.com/health"),
        ("https://api.example.com", None, "health", "https://api.example.com/health"),
    ],
)
def test_join_url(url, base_path, path, expected):
    assert _http.join_url(url, base_path, path) == expected


# ── _report ──────────────────────────────────────────────────────


def test_generated_at_is_one_format():
    import re

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", _report.generated_at())


def test_render_findings_emits_the_bullet_syntax_comment_py_reads():
    """comment.extract_failures reads `^\\s*-\\s*❌\\s*(.+?)$` — keep the shape."""
    import re

    lines = _report.render_findings("Issues", _report.FAIL_ICON, ["a broke", "b broke"])
    assert lines == ["**Issues:**", "- ❌ a broke", "- ❌ b broke", ""]
    pattern = re.compile(r"^\s*-\s*❌\s*(.+?)$")
    assert [pattern.match(l).group(1) for l in lines if pattern.match(l)] == ["a broke", "b broke"]


def test_render_findings_is_empty_when_nothing_to_render():
    assert _report.render_findings("Issues", "❌", []) == []


def test_render_skip_shape():
    assert _report.render_skip("no paths configured.", ["Set them:", "```yaml", "x: y", "```"]) == [
        "**Overall:** ⏭️ SKIPPED — no paths configured.",
        "",
        "Set them:",
        "```yaml",
        "x: y",
        "```",
        "",
    ]


def test_write_reports_writes_json_and_rendered_markdown(tmp_path):
    report_dir = tmp_path / "r"
    _report.write_reports(
        report_dir, report_dir / "x.json", report_dir / "x.md",
        {"status": "pass", "n": 1}, lambda r: f"# Report {r['status']}\n",
    )
    assert (report_dir / "x.md").read_text() == "# Report pass\n"
    assert '"n": 1' in (report_dir / "x.json").read_text()


def test_gha_run_url(monkeypatch):
    for var in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"):
        monkeypatch.delenv(var, raising=False)
    assert _report.gha_run_url() is None
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/site")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    assert _report.gha_run_url() == "https://github.com/acme/site/actions/runs/42"


# ── _playwright ──────────────────────────────────────────────────


def test_npx_available_uses_which(monkeypatch):
    monkeypatch.setattr(_playwright.shutil, "which", lambda _: "/usr/bin/npx")
    assert _playwright.npx_available() is True
    monkeypatch.setattr(_playwright.shutil, "which", lambda _: None)
    assert _playwright.npx_available() is False


def test_build_cmd_names_the_spec_and_reporter(monkeypatch):
    monkeypatch.setattr(_playwright.templates, "playwright_config", lambda: Path("/cfg/playwright.config.js"))
    monkeypatch.setattr(_playwright.templates, "playwright_spec", lambda name: Path(f"/cfg/tests/{name}.spec.ts"))
    cmd = _playwright.build_cmd("smoke", ci_mode=True)
    assert cmd[:3] == ["npx", "playwright", "test"]
    assert "--config=/cfg/playwright.config.js" in cmd
    assert "/cfg/tests/smoke.spec.ts" in cmd
    assert "--reporter=list,html" in cmd
    assert "--reporter=list" in _playwright.build_cmd("smoke", ci_mode=False)


def test_ensure_assets_ejected_ejects_config_and_the_named_spec(monkeypatch, capsys):
    ejected = []

    def fake(name):
        ejected.append(name)
        return Path(".ss") / name, True

    monkeypatch.setattr(_playwright.templates, "ensure_ejected", fake)
    _playwright.ensure_assets_ejected("accessibility")
    assert ejected == [_playwright.templates.PLAYWRIGHT_CONFIG_NAME, "tests/accessibility.spec.ts"]
    assert "ejected" in capsys.readouterr().out


def test_write_summary_pass_and_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(_playwright, "gha_run_url", lambda: "https://gh/run/1")
    md = tmp_path / "r" / "x.md"
    _playwright.write_summary(tmp_path / "r", md, "## Smoke", 0, "https://x", "it broke")
    text = md.read_text()
    assert "✅ PASSED" in text and "it broke" not in text
    _playwright.write_summary(tmp_path / "r", md, "## Smoke", 1, "https://x", "it broke")
    text = md.read_text()
    assert "❌ FAILED" in text and "it broke" in text and "https://gh/run/1" in text
