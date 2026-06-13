"""Tests for the templates resolver (Playwright + Lighthouse configs and
spec files: .ss/ override → package-data fallback)."""

from __future__ import annotations

from pathlib import Path

from slopstopper import templates


# ── package-data presence ────────────────────────────────────────


def test_package_data_dir_exists():
    assert templates.PACKAGE_DATA_DIR.exists()
    assert templates.PACKAGE_DATA_DIR.is_dir()


def test_bundled_playwright_config_exists():
    assert (templates.PACKAGE_DATA_DIR / templates.PLAYWRIGHT_CONFIG_NAME).exists()


def test_bundled_lighthouserc_exists():
    assert (templates.PACKAGE_DATA_DIR / templates.LIGHTHOUSERC_NAME).exists()


def test_bundled_lighthouserc_prod_exists():
    assert (templates.PACKAGE_DATA_DIR / templates.LIGHTHOUSERC_PROD_NAME).exists()


def test_bundled_spec_files_present():
    tests_dir = templates.PACKAGE_DATA_DIR / "tests"
    assert (tests_dir / "smoke.spec.ts").exists()
    assert (tests_dir / "accessibility.spec.ts").exists()
    assert (tests_dir / "broken-links.spec.ts").exists()


# ── fallback to package data ─────────────────────────────────────


def test_playwright_config_falls_back_to_package_data(isolated_cwd):
    assert templates.playwright_config() == (
        templates.PACKAGE_DATA_DIR / templates.PLAYWRIGHT_CONFIG_NAME
    )


def test_lighthouserc_falls_back_to_package_data(isolated_cwd):
    assert templates.lighthouserc() == (
        templates.PACKAGE_DATA_DIR / templates.LIGHTHOUSERC_NAME
    )


def test_lighthouserc_prod_falls_back_to_package_data(isolated_cwd):
    assert templates.lighthouserc(prod=True) == (
        templates.PACKAGE_DATA_DIR / templates.LIGHTHOUSERC_PROD_NAME
    )


def test_lighthouserc_prod_override_wins(isolated_cwd):
    override = isolated_cwd / ".ss" / "lighthouserc.prod.json"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("{}")
    resolved = templates.lighthouserc(prod=True)
    assert resolved == Path(".ss/lighthouserc.prod.json")


def test_lighthouserc_dev_ignores_prod_override(isolated_cwd):
    """A prod override mustn't get picked up when prod=False."""
    override = isolated_cwd / ".ss" / "lighthouserc.prod.json"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("{}")
    resolved = templates.lighthouserc(prod=False)
    assert resolved == (templates.PACKAGE_DATA_DIR / templates.LIGHTHOUSERC_NAME)


def test_playwright_spec_falls_back_to_package_data(isolated_cwd):
    assert templates.playwright_spec("smoke") == (
        templates.PACKAGE_DATA_DIR / "tests" / "smoke.spec.ts"
    )


# ── .ss/ override wins ───────────────────────────────────────────


def test_playwright_config_override_wins(isolated_cwd):
    override = isolated_cwd / ".ss" / "playwright.config.js"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("// custom config")
    resolved = templates.playwright_config()
    assert resolved == Path(".ss/playwright.config.js")


def test_lighthouserc_override_wins(isolated_cwd):
    override = isolated_cwd / ".ss" / "lighthouserc.json"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("{}")
    resolved = templates.lighthouserc()
    assert resolved == Path(".ss/lighthouserc.json")


def test_playwright_spec_override_wins(isolated_cwd):
    override = isolated_cwd / ".ss" / "tests" / "smoke.spec.ts"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("// custom spec")
    resolved = templates.playwright_spec("smoke")
    assert resolved == Path(".ss/tests/smoke.spec.ts")


def test_playwright_spec_override_only_for_named_check(isolated_cwd):
    # An override for `smoke` doesn't affect `accessibility`
    override = isolated_cwd / ".ss" / "tests" / "smoke.spec.ts"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("// custom smoke spec")

    smoke_resolved = templates.playwright_spec("smoke")
    a11y_resolved = templates.playwright_spec("accessibility")

    assert smoke_resolved == Path(".ss/tests/smoke.spec.ts")
    assert a11y_resolved == (
        templates.PACKAGE_DATA_DIR / "tests" / "accessibility.spec.ts"
    )
