"""`slopstopper demo` writes the fixture repo, and the fixture fails every
check it promises to fail, each with exactly its one finding, and passes
or skips the rest.

The static findings run in-process. The three scanner-backed checks run
the real tool and skip where it is not installed; the browser findings
serve the fixture's `app/` from a stdlib server, and the Playwright-backed
checks skip without the repo's `node_modules`, like test_specs_subpath.py.
"""

from __future__ import annotations

import csv
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from slopstopper import cli, config, demo
from slopstopper.checks import (
    csp_exceptions,
    docs_accuracy,
    docs_structure,
    entry_files,
    llms_txt,
    robots_txt,
    sast,
    seo,
    sitemap,
    vulnerability_all,
)
from slopstopper.checks import complexity as complexity_check

REPO_ROOT = Path(__file__).resolve().parents[2]
NODE_MODULES = REPO_ROOT / "node_modules"

needs_playwright = pytest.mark.skipif(
    (shutil.which("npx") is None or not (NODE_MODULES / "@playwright" / "test").is_dir()) and not os.environ.get("CI"),
    reason="needs node and the repo's Playwright install (npm ci)",
)


def needs_tool(name: str):
    return pytest.mark.skipif(shutil.which(name) is None, reason=f"needs {name} on PATH")


def test_the_fixture_has_the_agents_first_layout():
    names = [published for published, _ in demo.files()]
    for expected in (
        "README.md", "AGENTS.md", "CLAUDE.md", "docs/README.md",
        "docs/runbooks/RELEASE.md", "docs/security/CSP_EXCEPTIONS.md",
        ".slopstopper.yml", ".gitignore", ".env.example",
        "app/index.html", "app/history.html", "app/_headers", "app/sitemap.xml",
        "scripts/status.py", "scripts/requirements.txt", "package.json",
    ):
        assert expected in names
    assert not any(n in demo.RENAMES for n in names), "stored names are published renamed"


def test_write_creates_every_file_and_skips_existing_ones(tmp_path):
    dest = tmp_path / "lantern"
    written, skipped = demo.write(dest)
    assert sorted(written) == sorted(str(dest / n) for n, _ in demo.files())
    assert skipped == []
    assert (dest / "CLAUDE.md").read_text() == "@AGENTS.md\n"

    (dest / "README.md").write_text("# mine\n")
    written, skipped = demo.write(dest)
    assert written == [] and skipped == [str(dest / n) for n, _ in demo.files()]
    assert (dest / "README.md").read_text() == "# mine\n"

    written, _ = demo.write(dest, force=True)
    assert str(dest / "README.md") in written
    assert (dest / "README.md").read_text().startswith("# Lantern")


@pytest.fixture
def demo_cwd(tmp_path, monkeypatch):
    """A written demo repo as the current directory, with the config cache
    reset so the checks read its .slopstopper.yml."""
    dest = tmp_path / "slopstopper-demo"
    demo.write(dest)
    monkeypatch.chdir(dest)
    config.reload()
    yield dest
    config.reload()


def _git(*args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=demo@example.com", "-c", "user.name=demo", *args],
        check=True, capture_output=True,
    )


@pytest.fixture
def served_demo(demo_cwd):
    """`app/` served from a stdlib server; yields the base URL."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(demo_cwd / "app"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert text.count(old) == 1, f"{old!r} should appear once in {path}"
    path.write_text(text.replace(old, new))


# ── the static findings ──────────────────────────────────────────


def test_entry_files_fails_only_on_the_oversized_readme(demo_cwd):
    assert entry_files.run([]) == 1
    report = json.loads((demo_cwd / ".ss/reports/entry-files/entry-file-size-report.json").read_text())
    assert report["violation_count"] == 1
    over = [m["file"] for m in report["measurements"] if m.get("over_budget")]
    assert over == ["README.md"], report["measurements"]
    # The fix the demo names: move the manual out of the README.
    readme = demo_cwd / "README.md"
    head = readme.read_text().split("## Everything you need to know")[0]
    readme.write_text(head)
    assert entry_files.run([]) == 0


def test_docs_structure_fails_only_on_the_unrouted_runbook(demo_cwd):
    assert docs_structure.run([]) == 1
    report = json.loads((demo_cwd / ".ss/reports/docs/docs-structure-report.json").read_text())
    assert [(v["type"], v["path"]) for v in report["violations"]] == [
        ("unrouted_doc", "docs/runbooks/RELEASE.md"),
    ]
    # The fix the demo names: one route row in the map.
    doc_map = demo_cwd / "docs/README.md"
    anchor = "| opening a pull request, or reviewing one     |"
    assert anchor in doc_map.read_text()
    doc_map.write_text(doc_map.read_text().replace(
        anchor,
        "| cutting a release, or rolling one back       | Read [runbooks/RELEASE.md](runbooks/RELEASE.md) for the tag flow and the rollback rule |\n"
        + anchor,
    ))
    assert docs_structure.run([]) == 0


def test_docs_accuracy_fails_only_on_the_stale_task_reference(demo_cwd):
    assert docs_accuracy.run([]) == 1
    report = json.loads((demo_cwd / ".ss/reports/docs/docs-accuracy-report.json").read_text())
    assert [(i["type"], i["file"]) for i in report["issues"]] == [("stale_task_ref", "docs/contributing.md")]
    assert "task ss:hygiene:docs" in report["issues"][0]["message"]
    # The fix the demo names: say the commands that exist.
    _edit(
        demo_cwd / "docs/contributing.md",
        "Run `task ss:hygiene:docs` before you push; it is the two docs checks in\none,",
        "Run `slopstopper run hygiene:entry-files` and `slopstopper run\nhygiene:docs-structure` before you push;",
    )
    assert docs_accuracy.run([]) == 0


def test_complexity_fails_only_on_the_badge_if_chain(demo_cwd):
    assert complexity_check.run([]) == 1
    rows = list(csv.reader((demo_cwd / ".ss/reports/complexity/complexity-report.csv").read_text().splitlines()))
    over = [(r[7], int(r[1])) for r in rows if int(r[1]) > complexity_check.DEFAULT_MAX_CCN]
    assert over == [("badge", 17)], rows
    # The fix the demo names: a lookup table.
    script = demo_cwd / "scripts/status.py"
    text = script.read_text()
    start, end = text.index("def badge(status):"), text.index("def update(")
    script.write_text(
        text[:start]
        + "BADGES = {\n"
        + "    **dict.fromkeys((200, 201, 202, 204, 301, 302, 304), \"ok\"),\n"
        + "    **dict.fromkeys((400, 401, 403, 404, 408, 429), \"degraded\"),\n"
        + "    **dict.fromkeys((500, 502, 503), \"down\"),\n"
        + "}\n\n\ndef badge(status):\n    return BADGES.get(status, \"unknown\")\n\n\n"
        + text[end:]
    )
    assert complexity_check.run([]) == 0


def test_csp_exceptions_fails_only_on_the_undocumented_history_page(demo_cwd):
    assert csp_exceptions.run([]) == 1
    report = json.loads((demo_cwd / ".ss/reports/csp/csp-exceptions-report.json").read_text())
    assert [(i["severity"], i["path"]) for i in report["issues"]] == [("error", "/history.html")]
    assert "https://charts.example.com" in report["issues"][0]["message"]
    # The fix the demo names: write the exception down, every field.
    _edit(
        demo_cwd / "docs/security/CSP_EXCEPTIONS.md",
        "None yet: every path serves the baseline policy.\n",
        "### `/history.html`\n\n"
        "- **Origin allowed:** `https://charts.example.com`\n"
        "- **Directives added:** `img-src https://charts.example.com`\n"
        "- **Loader SRI:** n/a (an image, not a script)\n"
        "- **Why:** the uptime chart is rendered by the charts service\n"
        "- **Approved by:** the pull request that added the history page\n"
        "- **Data leaving site:** visitor IP and User-Agent when the image is fetched\n"
        "- **Refresh policy:** n/a\n",
    )
    assert csp_exceptions.run([]) == 0


# ── the scanner-backed findings ──────────────────────────────────


@needs_tool("semgrep")
def test_sast_fails_only_on_the_shell_true_commit(demo_cwd):
    assert sast.run([]) == 1
    data = json.loads((demo_cwd / ".ss/reports/sast/sast-report.json").read_text())
    blocking = [(r["check_id"], r["path"]) for r in data["results"] if sast._rank(r) >= sast.ERROR_RANK]
    assert blocking == [
        ("python.lang.security.audit.subprocess-shell-true.subprocess-shell-true", "scripts/status.py"),
    ]
    # The fix the demo names: a list, and no shell.
    _edit(
        demo_cwd / "scripts/status.py",
        'subprocess.run("git commit -qam \'status: " + " ".join(summary) + "\'", shell=True, check=False)',
        'subprocess.run(["git", "commit", "-qam", "status: " + " ".join(summary)], check=False)',
    )
    assert sast.run([]) == 0


@needs_tool("trivy")
def test_vulnerability_all_fails_only_on_the_requests_pin(demo_cwd):
    assert vulnerability_all.run([]) == 1
    data = json.loads((demo_cwd / ".ss/reports/vulnerability-all/vulnerability-all-report.json").read_text())
    critical, high, _medium, _low = vulnerability_all._collect_vulnerabilities(data)
    assert [(v["id"], v["pkg"], v["fixed"]) for v in critical + high] == [("CVE-2018-18074", "requests", "2.20.0")]
    # The fix the gate needs: the version the report's Fixed In column names.
    (demo_cwd / "scripts/requirements.txt").write_text("requests==2.20.0\n")
    assert vulnerability_all.run([]) == 0


# ── the served findings ──────────────────────────────────────────


def test_seo_fails_only_on_the_history_pages_description(served_demo, demo_cwd):
    assert seo.run(["--url", served_demo]) == 1
    report = json.loads((demo_cwd / ".ss/reports/seo/seo-metatags-report.json").read_text())
    failing = {p["url"].rsplit("/", 1)[1]: p["issues"] for p in report["pages"] if p["status"] != "pass"}
    assert failing == {"history.html": ['Missing <meta name="description">']}
    # The fix the demo names: one line in the head.
    _edit(
        demo_cwd / "app/history.html",
        "  <title>Lantern: incident history</title>\n",
        "  <title>Lantern: incident history</title>\n"
        '  <meta name="description" content="Every incident in the last ninety days, which service it hit and how long it lasted.">\n',
    )
    assert seo.run(["--url", served_demo]) == 0


def test_sitemap_fails_only_on_the_unlisted_history_page(served_demo, demo_cwd):
    assert sitemap.run(["--url", served_demo]) == 1
    report = json.loads((demo_cwd / ".ss/reports/sitemap/sitemap-report.json").read_text())
    assert report["issues"] == ["Reachable page missing from sitemap.xml: /history.html"]
    # The fix the demo names: list the page.
    _edit(
        demo_cwd / "app/sitemap.xml",
        "</urlset>",
        "  <url><loc>https://lantern.example.com/history.html</loc></url>\n</urlset>",
    )
    assert sitemap.run(["--url", served_demo]) == 0


def test_the_other_discovery_files_pass(served_demo):
    assert robots_txt.run(["--url", served_demo]) == 0
    assert llms_txt.run(["--url", served_demo]) == 0


def _run_browser_check(check: str, cwd: Path, url: str) -> subprocess.CompletedProcess:
    link = cwd / "node_modules"
    if not link.exists():
        link.symlink_to(NODE_MODULES)
    return subprocess.run(
        [sys.executable, "-m", "slopstopper", "run", check, "--", url],
        cwd=cwd, env={**os.environ}, capture_output=True, text=True, timeout=300,
    )


@needs_playwright
def test_accessibility_fails_only_on_the_charts_missing_alt(served_demo, demo_cwd):
    proc = _run_browser_check("reliability:accessibility", demo_cwd, served_demo)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "violations on /history.html (1 at or above" in proc.stdout
    assert "[CRITICAL] image-alt" in proc.stdout
    assert "violations on homepage" not in proc.stdout
    # The fix the demo names: say what the chart shows.
    _edit(
        demo_cwd / "app/history.html",
        '<img src="uptime.svg" width="480" height="60">',
        '<img src="uptime.svg" alt="Ninety days of uptime: two incidents" width="480" height="60">',
    )
    proc = _run_browser_check("reliability:accessibility", demo_cwd, served_demo)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@needs_playwright
@pytest.mark.parametrize("check", ["reliability:smoke", "reliability:e2e", "reliability:broken-links"])
def test_the_other_browser_checks_pass(check, served_demo, demo_cwd):
    proc = _run_browser_check(check, demo_cwd, served_demo)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── the command ──────────────────────────────────────────────────


def test_cli_writes_and_names_every_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["demo"]) == 0
    out = capsys.readouterr().out
    assert (tmp_path / demo.DEFAULT_OUT / "AGENTS.md").exists()
    for failure in demo.FAILURES:
        assert f"slopstopper run {failure['check']}" in out
    assert f"cd {demo.DEFAULT_OUT} && slopstopper run hygiene:entry-files" in out


def test_cli_json_shape(tmp_path, capsys):
    out_dir = tmp_path / "lantern"
    assert cli.main(["demo", "--out", str(out_dir), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data) == {"out", "written", "skipped", "failures"}
    assert data["out"] == str(out_dir)
    assert str(out_dir / ".slopstopper.yml") in data["written"]
    assert data["skipped"] == []
    assert [f["check"] for f in data["failures"]] == [f["check"] for f in demo.FAILURES]
    assert {f["check"] for f in demo.FAILURES} >= {
        "hygiene:entry-files", "hygiene:docs-structure", "hygiene:docs-accuracy", "hygiene:complexity",
        "security:sast", "security:vulnerability:all", "hygiene:csp-exceptions",
        "reliability:accessibility", "reliability:seo", "reliability:sitemap",
    }
    assert cli.main(["demo", "--out", str(out_dir), "--json"]) == 0
    again = json.loads(capsys.readouterr().out)
    assert again["written"] == [] and len(again["skipped"]) == len(data["written"])


def test_cli_refuses_a_file_as_out(tmp_path, capsys):
    target = tmp_path / "not-a-dir"
    target.write_text("x")
    assert cli.main(["demo", "--out", str(target)]) == 2
    assert "not a directory" in capsys.readouterr().err
    assert cli.main(["demo", "--out", str(target), "--json"]) == 2
    assert set(json.loads(capsys.readouterr().out)) == {"error"}


def test_cli_refuses_a_directory_where_a_file_belongs(tmp_path, capsys):
    dest = tmp_path / "lantern"
    (dest / "README.md").mkdir(parents=True)
    assert cli.main(["demo", "--out", str(dest)]) == 2
    assert "README.md is a directory" in capsys.readouterr().err
    assert cli.main(["demo", "--out", str(dest), "--force"]) == 2
    (dest / "docs").mkdir()
    (dest / "docs" / "runbooks").write_text("x")
    (dest / "README.md").rmdir()
    assert cli.main(["demo", "--out", str(dest), "--json"]) == 2
    assert "error" in json.loads(capsys.readouterr().out)


def test_quiet_keeps_only_the_result(tmp_path, capsys):
    assert cli.main(["--quiet", "demo", "--out", str(tmp_path / "q")]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_renames_are_keyed_by_whole_path_and_junk_is_skipped(monkeypatch, tmp_path):
    fake = tmp_path / "demo"
    (fake / "docs").mkdir(parents=True)
    (fake / "scripts").mkdir()
    (fake / "__pycache__").mkdir()
    (fake / "slopstopper.yml").write_text("profile: ui\n")
    (fake / "docs" / "slopstopper.yml").write_text("sample\n")
    (fake / "scripts" / "requirements.demo").write_text("requests==2.19.1\n")
    (fake / "docs" / "notes.md~").write_text("backup\n")
    (fake / "__pycache__" / "x.pyc").write_bytes(b"")
    (fake / ".DS_Store").write_bytes(b"")
    monkeypatch.setattr(demo, "DEMO_DIR", fake)
    assert sorted(n for n, _ in demo.files()) == [".slopstopper.yml", "docs/slopstopper.yml", "scripts/requirements.txt"]


def test_a_symlink_is_never_written_through(tmp_path):
    outside = tmp_path / "outside.md"
    dest = tmp_path / "lantern"
    dest.mkdir()
    (dest / "README.md").symlink_to(outside)          # dangling: exists() is False
    written, skipped = demo.write(dest)
    assert str(dest / "README.md") in skipped and str(dest / "README.md") not in written
    assert not outside.exists()

    outside.write_text("mine\n")
    written, _ = demo.write(dest, force=True)
    assert str(dest / "README.md") in written
    assert not (dest / "README.md").is_symlink()
    assert (dest / "README.md").read_text().startswith("# Lantern")
    assert outside.read_text() == "mine\n"


def test_the_hint_shell_quotes_the_destination(tmp_path, capsys):
    out_dir = tmp_path / "my demo"
    assert cli.main(["demo", "--out", str(out_dir)]) == 0
    assert f"cd '{out_dir}' && slopstopper run" in capsys.readouterr().out
