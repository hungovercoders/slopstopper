"""Tests for .ss/scripts/discover-pages.py.

Covers: env-var override, sitemap parsing (incl. sitemap-index recursion),
source-to-URL mapping, cross-cutting auto-escalation, unmapped modes,
resolution-order precedence, and the CLI shim.

Uses tempdir + chdir so the relative-path lookups (sitemap candidates,
.slopstopper.yml) resolve to fixtures. load_config caches; reload between
fixtures.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = THIS_DIR.parent / "scripts" / "discover-pages.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("discover_pages", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    spec.loader.exec_module(module)
    return module


def _enter_tmpdir() -> str:
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    return tmp


def _leave_tmpdir(tmp: str) -> None:
    os.chdir("/")
    shutil.rmtree(tmp, ignore_errors=True)


def _write_yml(text: str) -> None:
    Path(".slopstopper.yml").write_text(text)


def _reload_config(mod):
    """discover-pages.py uses load_config's module-level cache; reset between fixtures."""
    mod.load_config.reload()


def _clear_check_env():
    for var in ("SMOKE_PAGES", "ACCESSIBILITY_PAGES", "SEO_PAGES", "BROKEN_LINKS_PAGES"):
        os.environ.pop(var, None)


def test_env_var_override_short_circuits_everything():
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        os.environ["SEO_PAGES"] = "/from-env,/also-from-env"
        try:
            paths = mod.discover("seo", "pr")
            assert paths == ["/from-env", "/also-from-env"], paths
            print("✅ test_env_var_override_short_circuits_everything passed")
        finally:
            _clear_check_env()
    finally:
        _leave_tmpdir(tmp)


def test_falls_back_to_pages_list_when_no_coverage_mode():
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        _write_yml("pages:\n  seo: /,/about,/contact\n")
        _reload_config(mod)
        paths = mod.discover("seo", "pr")
        assert paths == ["/", "/about", "/contact"], paths
        print("✅ test_falls_back_to_pages_list_when_no_coverage_mode passed")
    finally:
        _leave_tmpdir(tmp)


def test_defaults_to_slash_when_nothing_configured():
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        _reload_config(mod)
        paths = mod.discover("accessibility", "main")
        assert paths == ["/"], paths
        print("✅ test_defaults_to_slash_when_nothing_configured passed")
    finally:
        _leave_tmpdir(tmp)


def test_sitemap_mode_extracts_paths_from_urlset():
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        Path("dist").mkdir()
        Path("dist/sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url><loc>https://example.com/</loc></url>\n'
            '  <url><loc>https://example.com/blog/</loc></url>\n'
            '  <url><loc>https://example.com/blog/post-a/</loc></url>\n'
            '</urlset>\n'
        )
        _write_yml("reliability:\n  coverage:\n    main: sitemap\n")
        _reload_config(mod)
        paths = mod.discover("seo", "main")
        assert paths == ["/", "/blog/", "/blog/post-a/"], paths
        print("✅ test_sitemap_mode_extracts_paths_from_urlset passed")
    finally:
        _leave_tmpdir(tmp)


def test_sitemap_mode_recurses_through_sitemap_index():
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        Path("dist/client").mkdir(parents=True)
        Path("dist/client/sitemap-index.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <sitemap><loc>https://example.com/sitemap-0.xml</loc></sitemap>\n'
            '</sitemapindex>\n'
        )
        Path("dist/client/sitemap-0.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url><loc>https://example.com/blog/a/</loc></url>\n'
            '  <url><loc>https://example.com/blog/b/</loc></url>\n'
            '</urlset>\n'
        )
        _write_yml("reliability:\n  coverage:\n    main: sitemap\n")
        _reload_config(mod)
        paths = mod.discover("seo", "main")
        assert paths == ["/blog/a/", "/blog/b/"], paths
        print("✅ test_sitemap_mode_recurses_through_sitemap_index passed")
    finally:
        _leave_tmpdir(tmp)


def test_explicit_list_mode_returns_verbatim():
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        _write_yml(
            "reliability:\n"
            "  coverage:\n"
            "    main: /,/pricing,/about\n"
            "pages:\n"
            "  seo: /should-be-shadowed\n"
        )
        _reload_config(mod)
        paths = mod.discover("seo", "main")
        assert paths == ["/", "/pricing", "/about"], paths
        print("✅ test_explicit_list_mode_returns_verbatim passed")
    finally:
        _leave_tmpdir(tmp)


def test_changed_mode_uses_astro_defaults(monkey):
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        Path("astro.config.mjs").write_text("export default {};\n")
        _write_yml("reliability:\n  coverage:\n    pr: changed\n")
        _reload_config(mod)
        monkey(
            mod,
            "_git_diff_files",
            lambda base_ref: [
                "src/content/blog/2026-06-12-hello.md",
                "src/pages/about.astro",
            ],
        )
        paths = mod.discover("accessibility", "pr")
        assert paths == ["/blog/2026-06-12-hello/", "/about/"], paths
        print("✅ test_changed_mode_uses_astro_defaults passed")
    finally:
        _leave_tmpdir(tmp)


def test_changed_mode_detects_nextjs_app_router(monkey):
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        Path("next.config.js").write_text("module.exports = {};\n")
        _write_yml("reliability:\n  coverage:\n    pr: changed\n")
        _reload_config(mod)
        monkey(
            mod,
            "_git_diff_files",
            lambda base_ref: ["app/about/page.tsx", "app/page.tsx"],
        )
        paths = mod.discover("seo", "pr")
        assert paths == ["/about/", "/"], paths
        print("✅ test_changed_mode_detects_nextjs_app_router passed")
    finally:
        _leave_tmpdir(tmp)


def test_cross_cutting_escalates_to_sitemap(monkey):
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        Path("dist").mkdir()
        Path("dist/sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url><loc>https://x.example/</loc></url>\n'
            '  <url><loc>https://x.example/a/</loc></url>\n'
            '</urlset>\n'
        )
        _write_yml(
            "reliability:\n"
            "  coverage:\n"
            "    pr: changed\n"
            "    cross_cutting_paths: ['src/styles/*']\n"
        )
        _reload_config(mod)
        monkey(
            mod,
            "_git_diff_files",
            lambda base_ref: [
                "src/content/blog/foo.md",
                "src/styles/global.css",
            ],
        )
        paths = mod.discover("seo", "pr")
        assert paths == ["/", "/a/"], paths
        print("✅ test_cross_cutting_escalates_to_sitemap passed")
    finally:
        _leave_tmpdir(tmp)


def test_unmapped_changed_file_falls_back_to_sitemap(monkey):
    """When every changed file is unmapped (e.g. infra changes), discovery
    should fall through to a sitemap sweep rather than silently no-op."""
    tmp = _enter_tmpdir()
    try:
        mod = _load_module()
        _clear_check_env()
        Path("astro.config.mjs").write_text("{}\n")
        Path("dist").mkdir()
        Path("dist/sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url><loc>https://x.example/fallback/</loc></url>\n'
            '</urlset>\n'
        )
        _write_yml("reliability:\n  coverage:\n    pr: changed\n")
        _reload_config(mod)
        monkey(mod, "_git_diff_files", lambda base_ref: ["infra/Dockerfile"])
        paths = mod.discover("seo", "pr")
        assert paths == ["/fallback/"], paths
        print("✅ test_unmapped_changed_file_falls_back_to_sitemap passed")
    finally:
        _leave_tmpdir(tmp)


def test_cli_shim_prints_comma_separated(monkey):
    tmp = _enter_tmpdir()
    try:
        Path("dist").mkdir()
        Path("dist/sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url><loc>https://x.example/</loc></url>\n'
            '  <url><loc>https://x.example/about/</loc></url>\n'
            '</urlset>\n'
        )
        _write_yml("reliability:\n  coverage:\n    cron: sitemap\n")
        env = {**os.environ}
        for var in ("SMOKE_PAGES", "ACCESSIBILITY_PAGES", "SEO_PAGES", "BROKEN_LINKS_PAGES"):
            env.pop(var, None)
        result = subprocess.run(
            ["python3", str(SCRIPT_PATH), "seo", "--event=cron"],
            capture_output=True,
            text=True,
            cwd=tmp,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "/,/about/", result.stdout
        print("✅ test_cli_shim_prints_comma_separated passed")
    finally:
        _leave_tmpdir(tmp)


# ── Lightweight monkeypatch — no pytest dependency ──

class _Monkey:
    def __init__(self):
        self._restore = []

    def __call__(self, mod, attr, value):
        original = getattr(mod, attr)
        setattr(mod, attr, value)
        self._restore.append((mod, attr, original))

    def undo(self):
        for mod, attr, original in self._restore:
            setattr(mod, attr, original)
        self._restore.clear()


def run_test(fn):
    """Invoke a test, supplying _Monkey() if the test wants one."""
    monkey = _Monkey()
    try:
        if fn.__code__.co_argcount == 0:
            fn()
        else:
            fn(monkey)
    finally:
        monkey.undo()


if __name__ == "__main__":
    print("\n🧪 Running discover-pages tests...\n")
    tests = [
        test_env_var_override_short_circuits_everything,
        test_falls_back_to_pages_list_when_no_coverage_mode,
        test_defaults_to_slash_when_nothing_configured,
        test_sitemap_mode_extracts_paths_from_urlset,
        test_sitemap_mode_recurses_through_sitemap_index,
        test_explicit_list_mode_returns_verbatim,
        test_changed_mode_uses_astro_defaults,
        test_changed_mode_detects_nextjs_app_router,
        test_cross_cutting_escalates_to_sitemap,
        test_unmapped_changed_file_falls_back_to_sitemap,
        test_cli_shim_prints_comma_separated,
    ]
    try:
        for test in tests:
            run_test(test)
        print("\n✅ All tests passed!\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
