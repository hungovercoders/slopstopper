"""Tests for the hygiene:privacy check."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopstopper import config
from slopstopper.checks import privacy, smoke


WRANGLER_LOGS_OFF = '{\n  // comment\n  "name": "site",\n  "observability": { "enabled": false },\n}\n'
WRANGLER_LOGS_ON = '{ "name": "site", "observability": { "enabled": true } }\n'
HEADERS_JSON = json.dumps([
    {"for": "/*", "values": {"Content-Security-Policy": "default-src 'self'; script-src 'self'; frame-ancestors https://embedder.example"}},
    {"for": "/feedback.html", "values": {"Content-Security-Policy": "default-src 'self'; script-src 'self' https://giscus.app; connect-src https://api.github.com; frame-src https://giscus.app"}},
])

GOOD_PAGE = """<!doctype html><html><body>
<h1>Privacy</h1>
<p>This site is hosted on Cloudflare, which keeps aggregate traffic statistics and no per-request logs.</p>
<p>The feedback page loads comments from giscus.app when you press the button; that reaches GitHub.</p>
<p>Last checked against the site's configuration on <time datetime="2026-10-24">24 October 2026</time>.</p>
<footer><a href="privacy.html">Privacy</a></footer>
</body></html>
"""


@pytest.fixture
def site(isolated_cwd: Path, write_config):
    """A ui repo on Cloudflare with a CSP source and a good statement."""
    (isolated_cwd / "wrangler.jsonc").write_text(WRANGLER_LOGS_OFF)
    (isolated_cwd / "worker").mkdir()
    (isolated_cwd / "worker/headers.json").write_text(HEADERS_JSON)
    (isolated_cwd / "app").mkdir()
    (isolated_cwd / "app/privacy.html").write_text(GOOD_PAGE)
    write_config("profile: ui\nheaders:\n  source: worker/headers.json\n  format: json\n")
    return isolated_cwd


def _issues() -> list[str]:
    return [i["rule"] for i in json.loads(Path(".ss/reports/privacy/privacy-report.json").read_text())["issues"]]


# ── when it applies ──────────────────────────────────────────────


def test_no_host_evidence_is_a_graceful_skip(isolated_cwd, write_config, capsys):
    write_config("profile: ui\n")
    assert privacy.run() == 0
    assert "no hosting config" in capsys.readouterr().out
    assert not Path(".ss/reports/privacy").exists()


def test_urls_production_alone_is_host_evidence(isolated_cwd, write_config):
    write_config("profile: ui\nurls:\n  production: https://example.com\n")
    assert privacy.run() == 1
    assert _issues() == ["page"]


@pytest.mark.parametrize("profile", ["api", "library"])
def test_api_and_library_profiles_never_run_it(site, write_config, profile, capsys):
    write_config(f"profile: {profile}\n")
    (site / "app/privacy.html").unlink()
    assert privacy.run() == 0
    assert "profile drops it" in capsys.readouterr().out


def test_opt_out_is_visible(site, write_config, capsys):
    write_config("profile: ui\nprivacy:\n  page: ''\n")
    (site / "app/privacy.html").unlink()
    assert privacy.run() == 0
    assert "opted out" in capsys.readouterr().out


def test_arguments_are_rejected(site):
    assert privacy.run(["--url", "x"]) == 2


# ── rule 1: a page exists ────────────────────────────────────────


def test_missing_page_names_the_candidates_and_the_host(site, capsys):
    (site / "app/privacy.html").unlink()
    assert privacy.run() == 1
    out = capsys.readouterr().out
    assert "no privacy page found" in out
    assert "privacy.html" in out and "Cloudflare" in out
    assert _issues() == ["page"]


def test_configured_page_that_does_not_exist_fails(site, write_config):
    write_config("profile: ui\nprivacy:\n  page: legal/privacy.md\n")
    assert privacy.run() == 1
    assert _issues() == ["page"]


def test_auto_discovery_finds_nested_pages_in_any_framework(isolated_cwd, write_config):
    (isolated_cwd / "netlify.toml").write_text("[build]\n")
    page = isolated_cwd / "website/src/content/docs/privacy.md"
    page.parent.mkdir(parents=True)
    page.write_text("Hosted on Netlify. Last updated 3 March 2026.\n")
    write_config("profile: ui\n")
    assert privacy.resolve_page()[0] == page
    assert privacy.run() == 0


def test_auto_discovery_skips_hidden_directories(site):
    """A worktree or cache under a dot-directory can hold a copy of the
    whole repo; its privacy page is not this repo's page."""
    copy = site / ".claude/worktrees/agent-1/app/privacy.html"
    copy.parent.mkdir(parents=True)
    copy.write_text(GOOD_PAGE)
    page, _ = privacy.resolve_page(site)
    assert page == site / "app/privacy.html"
    (site / ".tool/wrangler.toml").parent.mkdir()
    (site / ".tool/wrangler.toml").write_text("[observability]\nenabled = true\n")
    assert privacy._host_config(site) == (site / "wrangler.jsonc", "Cloudflare")


def test_auto_discovery_skips_build_output(isolated_cwd, write_config):
    (isolated_cwd / "vercel.json").write_text("{}\n")
    built = isolated_cwd / "dist/privacy.html"
    built.parent.mkdir()
    built.write_text("stale")
    src = isolated_cwd / "src/pages/privacy/index.astro"
    src.parent.mkdir(parents=True)
    src.write_text("Vercel hosts this. 2026-01-02\n")
    write_config("profile: ui\n")
    assert privacy.resolve_page()[0] == src


# ── rules 2 to 5 ─────────────────────────────────────────────────


def test_a_matching_statement_passes(site, capsys):
    assert privacy.run() == 0
    out = capsys.readouterr().out
    assert "matches the site's configuration" in out
    report = Path(".ss/reports/privacy/privacy-report.md").read_text()
    assert "✅ PASS" in report
    assert "`https://giscus.app`" in report and "`https://api.github.com`" in report
    assert "embedder.example" not in report, "frame-ancestors is who may embed us, not who we reach"


def test_page_must_name_the_host(site, capsys):
    (site / "app/privacy.html").write_text(GOOD_PAGE.replace("Cloudflare", "our host"))
    assert privacy.run() == 1
    assert "does not name Cloudflare" in capsys.readouterr().out
    assert _issues() == ["host"]


def test_page_must_name_every_third_party_the_csp_allows(site, capsys):
    (site / "app/privacy.html").write_text(GOOD_PAGE.replace("giscus.app", "a comments widget"))
    assert privacy.run() == 1
    out = capsys.readouterr().out
    assert "does not name `giscus.app`" in out and "(or `giscus`)" in out
    assert _issues() == ["third-party"]


def test_the_distinguishing_label_is_enough(site):
    """terminalofterror.com says "a code highlighter from cdnjs" and "GitHub"
    for cdnjs.cloudflare.com and api.github.com; that names them."""
    (site / "worker/headers.json").write_text(json.dumps([
        {"for": "/*", "values": {"Content-Security-Policy": "default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; connect-src 'self' https://api.github.com"}},
    ]))
    (site / "app/privacy.html").write_text(
        "<p>Hosted on Cloudflare. A code highlighter from cdnjs; the home page asks GitHub for the latest release.</p><p>24 October 2026</p>"
    )
    assert privacy.run() == 0


def test_any_service_label_or_its_operator_is_enough(site):
    page = site / "app/privacy.html"
    page.write_text(GOOD_PAGE.replace("Cloudflare,", "Cloudflare (which also serves the Turnstile challenge and fonts via Google),"))
    (site / "worker/headers.json").write_text(json.dumps([{"for": "/*", "values": {"Content-Security-Policy":
        "default-src 'self'; script-src https://challenges.cloudflare.com; font-src https://fonts.gstatic.com; connect-src https://*.sentry.io"}}]))
    assert privacy.run() == 1
    assert _issues() == ["third-party"]
    assert json.loads(Path(".ss/reports/privacy/privacy-report.json").read_text())["issues"][0]["message"].count("sentry.io") == 1
    page.write_text(page.read_text().replace("via Google)", "via Google; errors go to Sentry)"))
    assert privacy.run() == 0


def test_extra_hosts_from_config_are_required(site, write_config, capsys):
    write_config("profile: ui\nheaders:\n  source: worker/headers.json\n  format: json\nprivacy:\n  hosts: [Fastly]\n")
    assert privacy.run() == 1
    assert "does not name Fastly" in capsys.readouterr().out


def test_workers_logs_on_requires_a_logs_mention(site, capsys):
    (site / "wrangler.jsonc").write_text(WRANGLER_LOGS_ON)
    (site / "app/privacy.html").write_text(GOOD_PAGE.replace("and no per-request logs", ""))
    assert privacy.run() == 1
    assert "turns Workers Logs on" in capsys.readouterr().out
    assert _issues() == ["logs"]


def test_workers_logs_on_in_toml(site):
    (site / "wrangler.jsonc").unlink()
    (site / "wrangler.toml").write_text('name = "site"\n\n[observability]\nenabled = true\n')
    assert privacy._logs_enabled(site / "wrangler.toml") is True
    (site / "wrangler.toml").write_text('name = "site"\n\n[observability]\nenabled = false\n')
    assert privacy._logs_enabled(site / "wrangler.toml") is False


def test_jsonc_strings_and_comments_do_not_confuse_the_parse():
    text = (
        '{\n'
        '  "name": "s", // see "docs"\n'
        '  "url": "https://x.y/z", /* "quoted" */\n'
        '  "observability": { "logs": { "enabled": true, }, },\n'
        '}\n'
    )
    assert json.loads(privacy._strip_jsonc(text)) == {"name": "s", "url": "https://x.y/z", "observability": {"logs": {"enabled": True}}}


@pytest.mark.parametrize("text, expected", [
    ('[observability] # comment\nenabled = true\n', True),
    ('observability = { enabled = true }\n', True),
    ('[observability]\nenabled = false\n[observability.logs]\nenabled = true\n', True),
    ('observability.enabled = true\n', True),
    ('[observability]\nenabled = false\n', False),
    ('name = "site"\n', False),
])
def test_workers_logs_in_every_toml_shape(site, text, expected):
    (site / "wrangler.toml").write_text(text)
    assert privacy._logs_enabled(site / "wrangler.toml") is expected


def test_an_unparseable_wrangler_config_is_said_not_assumed_off(site, capsys):
    (site / "wrangler.jsonc").write_text('{ "observability": { "enabled": true ')
    assert privacy._logs_enabled(site / "wrangler.jsonc") is None
    (site / "app/privacy.html").write_text(GOOD_PAGE.replace("and no per-request logs", ""))
    assert privacy.run() == 0
    assert "could not be parsed" in capsys.readouterr().out


def test_wrangler_one_directory_down_counts(isolated_cwd, write_config):
    (isolated_cwd / "website").mkdir()
    (isolated_cwd / "website/wrangler.jsonc").write_text(WRANGLER_LOGS_OFF)
    write_config("profile: ui\n")
    assert privacy._host_config(isolated_cwd) == (isolated_cwd / "website/wrangler.jsonc", "Cloudflare")


def test_page_must_carry_a_date(site, capsys):
    (site / "app/privacy.html").write_text(GOOD_PAGE.replace('<time datetime="2026-10-24">24 October 2026</time>', "recently"))
    assert privacy.run() == 1
    assert "carries no date" in capsys.readouterr().out
    assert _issues() == ["date"]


@pytest.mark.parametrize("text", ["2026-10-24", "24 October 2026", "October 24, 2026", "3rd March 2026"])
def test_date_forms(text):
    assert privacy.DATE_RE.search(f"Last checked {text}.")


def test_script_and_style_blocks_do_not_count_as_naming(site):
    (site / "app/privacy.html").write_text(
        GOOD_PAGE.replace("giscus.app", "a widget") + "<script>fetch('https://giscus.app')</script>"
    )
    assert privacy.run() == 1
    assert _issues() == ["third-party"]


def test_every_issue_is_reported_together(site):
    (site / "wrangler.jsonc").write_text(WRANGLER_LOGS_ON)
    (site / "app/privacy.html").write_text("<p>We respect your privacy.</p>")
    assert privacy.run() == 1
    assert _issues() == ["host", "logs", "third-party", "third-party", "date"]


# ── the smoke-test link rule ─────────────────────────────────────


def test_page_url_is_derived_from_the_page_name(site, write_config):
    assert privacy.page_url() == "/privacy.html"
    (site / "app/privacy.html").unlink()
    nested = site / "src/content/docs/privacy.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("x")
    assert privacy.page_url() == "/privacy/"
    write_config("profile: ui\nprivacy:\n  url: /legal/privacy\n")
    assert privacy.page_url() == "/legal/privacy"
    write_config("profile: ui\nprivacy:\n  require_link: false\n")
    assert privacy.page_url() is None
    write_config("profile: ui\nprivacy:\n  page: ''\n")
    assert privacy.page_url() is None


def test_smoke_passes_the_privacy_url_to_the_spec(site):
    env = smoke._build_env("http://localhost:8099", ci_mode=False)
    assert env["SMOKE_PRIVACY_URL"] == "/privacy.html"


def test_smoke_link_rule_applies_only_where_the_check_does(site, write_config):
    """A `library` repo with a stray privacy.md, or a ui repo with no host
    evidence, must not start failing smoke on every page after a CLI bump."""
    write_config("profile: library\nheaders:\n  source: worker/headers.json\n  format: json\n")
    config.reload()
    assert privacy.page_url() is None
    assert "SMOKE_PRIVACY_URL" not in smoke._build_env("http://localhost:8099", ci_mode=False)
    write_config("profile: ui\n")
    config.reload()
    (site / "wrangler.jsonc").unlink()
    assert privacy.page_url() is None
    (site / "wrangler.jsonc").write_text(WRANGLER_LOGS_OFF)
    assert privacy.page_url() == "/privacy.html"


def test_smoke_omits_the_privacy_url_when_there_is_no_page(isolated_cwd, write_config):
    write_config("profile: ui\n")
    config.reload()
    env = smoke._build_env("http://localhost:8099", ci_mode=False)
    assert "SMOKE_PRIVACY_URL" not in env
