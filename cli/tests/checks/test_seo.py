"""Tests for the reliability:seo check (subprocess wrapper around
check-seo-metatags.py)."""

from __future__ import annotations

import subprocess

from slopstopper.checks import seo


def test_parse_args_defaults():
    parsed = seo._parse_args(None)
    assert parsed.url is None
    assert parsed.pages is None
    assert parsed.no_require_og_image is False
    assert parsed.no_verify_og_image is False
    assert parsed.og_image_base is None


def test_parse_args_explicit():
    parsed = seo._parse_args([
        "--url", "https://example.com",
        "--pages", "/,/blog",
        "--no-require-og-image",
        "--no-verify-og-image",
        "--og-image-base", "http://localhost:8080",
    ])
    assert parsed.url == "https://example.com"
    assert parsed.pages == "/,/blog"
    assert parsed.no_require_og_image is True
    assert parsed.no_verify_og_image is True
    assert parsed.og_image_base == "http://localhost:8080"


def test_resolve_url_prefers_flag(monkeypatch):
    monkeypatch.setenv("SEO_TEST_URL", "https://from-env")
    assert seo._resolve_url("https://from-flag") == "https://from-flag"


def test_resolve_url_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("SEO_TEST_URL", "https://from-env")
    assert seo._resolve_url(None) == "https://from-env"


def test_resolve_url_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("SEO_TEST_URL", raising=False)
    assert seo._resolve_url(None) is None


def test_discover_pages_returns_none_when_script_missing(isolated_cwd):
    assert seo._discover_pages() is None


def test_discover_pages_returns_stdout_when_script_succeeds(monkeypatch, isolated_cwd):
    seo.DISCOVER_PAGES.parent.mkdir(parents=True, exist_ok=True)
    seo.DISCOVER_PAGES.write_text("# stub")

    monkeypatch.setattr(
        seo.subprocess, "run",
        lambda cmd, capture_output, text, check: subprocess.CompletedProcess(
            cmd, 0, stdout="/,/blog\n", stderr=""
        ),
    )
    assert seo._discover_pages() == "/,/blog"


def test_discover_pages_returns_none_on_non_zero_exit(monkeypatch, isolated_cwd):
    seo.DISCOVER_PAGES.parent.mkdir(parents=True, exist_ok=True)
    seo.DISCOVER_PAGES.write_text("# stub")

    monkeypatch.setattr(
        seo.subprocess, "run",
        lambda cmd, capture_output, text, check: subprocess.CompletedProcess(
            cmd, 1, stdout="ignore", stderr="error"
        ),
    )
    assert seo._discover_pages() is None


def test_build_env_threads_url(isolated_cwd, monkeypatch):
    monkeypatch.delenv("SEO_PAGES", raising=False)
    monkeypatch.setattr(seo, "_discover_pages", lambda: None)
    parsed = seo._parse_args(["--url", "https://example.com"])
    env = seo._build_env(parsed, "https://example.com")
    assert env["SEO_TEST_URL"] == "https://example.com"


def test_build_env_pages_flag_overrides_discovery(isolated_cwd, monkeypatch):
    monkeypatch.setattr(seo, "_discover_pages", lambda: "/should-not-use")
    parsed = seo._parse_args(["--url", "https://example.com", "--pages", "/explicit"])
    env = seo._build_env(parsed, "https://example.com")
    assert env["SEO_PAGES"] == "/explicit"


def test_build_env_uses_discover_pages_when_unset(isolated_cwd, monkeypatch):
    monkeypatch.delenv("SEO_PAGES", raising=False)
    monkeypatch.setattr(seo, "_discover_pages", lambda: "/,/from-discover")
    parsed = seo._parse_args(["--url", "https://example.com"])
    env = seo._build_env(parsed, "https://example.com")
    assert env["SEO_PAGES"] == "/,/from-discover"


def test_build_env_preserves_caller_pages(monkeypatch):
    monkeypatch.setenv("SEO_PAGES", "/preset")
    monkeypatch.setattr(seo, "_discover_pages", lambda: "/should-not-use")
    parsed = seo._parse_args(["--url", "https://example.com"])
    env = seo._build_env(parsed, "https://example.com")
    assert env["SEO_PAGES"] == "/preset"


def test_build_env_threads_og_image_flags(isolated_cwd, monkeypatch):
    monkeypatch.setattr(seo, "_discover_pages", lambda: None)
    parsed = seo._parse_args([
        "--url", "https://example.com",
        "--no-require-og-image",
        "--no-verify-og-image",
        "--og-image-base", "http://local",
    ])
    env = seo._build_env(parsed, "https://example.com")
    assert env["SEO_REQUIRE_OG_IMAGE"] == "0"
    assert env["SEO_VERIFY_OG_IMAGE"] == "0"
    assert env["SEO_OG_IMAGE_BASE"] == "http://local"


def test_build_env_omits_og_image_flags_by_default(isolated_cwd, monkeypatch):
    monkeypatch.delenv("SEO_REQUIRE_OG_IMAGE", raising=False)
    monkeypatch.delenv("SEO_VERIFY_OG_IMAGE", raising=False)
    monkeypatch.delenv("SEO_OG_IMAGE_BASE", raising=False)
    monkeypatch.setattr(seo, "_discover_pages", lambda: None)
    parsed = seo._parse_args(["--url", "https://example.com"])
    env = seo._build_env(parsed, "https://example.com")
    assert "SEO_REQUIRE_OG_IMAGE" not in env
    assert "SEO_VERIFY_OG_IMAGE" not in env
    assert "SEO_OG_IMAGE_BASE" not in env


# ── subprocess / runtime ─────────────────────────────────────────


def test_run_returns_one_when_url_missing(monkeypatch, isolated_cwd, capsys):
    monkeypatch.delenv("SEO_TEST_URL", raising=False)
    rc = seo.run([])
    assert rc == 1
    assert "SEO target URL is required" in capsys.readouterr().out


def test_run_returns_one_when_script_missing(monkeypatch, isolated_cwd, capsys):
    rc = seo.run(["--url", "https://example.com"])
    assert rc == 1
    assert "SEO script not found" in capsys.readouterr().out


def test_run_invokes_seo_script(monkeypatch, isolated_cwd):
    seo.SCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    seo.SCRIPT_PATH.write_text("# stub")

    captured: dict = {}

    def fake_run(cmd, env, check):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(seo, "_discover_pages", lambda: None)
    monkeypatch.setattr(seo.subprocess, "run", fake_run)

    rc = seo.run(["--url", "https://example.com"])
    assert rc == 0
    assert str(seo.SCRIPT_PATH) in captured["cmd"]
    assert captured["env"]["SEO_TEST_URL"] == "https://example.com"


def test_run_propagates_script_failure(monkeypatch, isolated_cwd):
    seo.SCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    seo.SCRIPT_PATH.write_text("# stub")

    monkeypatch.setattr(seo, "_discover_pages", lambda: None)
    monkeypatch.setattr(
        seo.subprocess, "run",
        lambda cmd, env, check: subprocess.CompletedProcess(cmd, 1),
    )

    rc = seo.run(["--url", "https://example.com"])
    assert rc == 1
