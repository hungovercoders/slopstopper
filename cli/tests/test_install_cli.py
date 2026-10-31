"""`slopstopper install` writes the suite into a repo from the files the
CLI ships, and a re-run refreshes what slopstopper owns and leaves what
the adopter owns alone.

Each test runs the CLI as a subprocess against a throwaway target, the
way an adopter does, so the config cache, the working directory and the
PATH are the real ones. The repo-topic step shells out to `gh`; it is off
by default here and the topic tests put a fake one on PATH.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from slopstopper import __version__, suite

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "cli" / "slopstopper" / "data"
STARTER = REPO_ROOT / "templates" / "slopstopper.yml.starter"
EXAMPLE = REPO_ROOT / ".slopstopper.yml.example"


def _run_install(target: Path, *, args: list[str] | None = None, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["SLOPSTOPPER_NO_TOPIC"] = "1"
    if env_extra:
        env.update(env_extra)
    env = {k: v for k, v in env.items() if v is not None}
    return subprocess.run(
        [sys.executable, "-m", "slopstopper", "install", *(args or []), str(target)],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT,
    )


def _make_minimal_target(tmp_path: Path) -> Path:
    """The least a target needs: a git repo with public/."""
    target = tmp_path / "adopter"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    (target / "public").mkdir()
    return target


def _installed(target: Path) -> set[str]:
    return {p.name for p in (target / ".github/workflows").glob("ss-*.yml")}


def _profile_key(target: Path) -> str | None:
    for line in (target / ".slopstopper.yml").read_text().splitlines():
        if line.startswith("profile:"):
            return line.split(":", 1)[1].strip()
    return None


def _read_pin(target: Path) -> str | None:
    cfg = target / "mise.toml"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        if "pipx:slopstopper-cli" in line and "=" in line:
            return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


# ── what lands ───────────────────────────────────────────────────


def test_a_fresh_install_writes_the_suite(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert (target / "Taskfile.ss.yml").read_text() == (REPO_ROOT / "Taskfile.ss.yml").read_text()
    assert "taskfile: ./Taskfile.ss.yml" in (target / "Taskfile.yml").read_text()
    assert (target / ".slopstopper.yml").read_text() == STARTER.read_text()
    for action in ("ss-setup", "ss-resolve-url", "ss-playwright"):
        assert (target / ".github/actions" / action / "action.yml").is_file(), action
    assert (target / ".github/labeler.yml").is_file()
    assert (target / ".zap/rules.tsv").is_file()
    assert (target / ".markdownlint.json").is_file()
    for name in ("README.md", "AGENTS.md", "CLAUDE.md", "docs/README.md"):
        assert (target / name).is_file(), name
    assert (target / ".ss/.installed-from").read_text() == f"{__version__}\n"
    assert "Installation complete" in result.stdout


def test_the_files_come_from_the_suite_the_cli_carries(tmp_path):
    """Every workflow on disk is byte-for-byte the one this CLI ships."""
    target = _make_minimal_target(tmp_path)
    (target / "openapi.yaml").write_text("openapi: 3.0.0\n")
    assert _run_install(target).returncode == 0
    root = suite.source_root()
    for name in _installed(target):
        assert (target / ".github/workflows" / name).read_bytes() == (root / ".github/workflows" / name).read_bytes(), name


def test_an_existing_taskfile_is_left_alone_with_the_include_to_add(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "Taskfile.yml").write_text("version: '3'\ntasks:\n  build:\n    cmds: [echo hi]\n")
    result = _run_install(target)
    assert result.returncode == 0, result.stderr
    assert "build:" in (target / "Taskfile.yml").read_text()
    assert "taskfile: ./Taskfile.ss.yml" in result.stdout


def test_a_taskfile_that_already_includes_the_shims_needs_nothing(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "Taskfile.yml").write_text("version: '3'\nincludes:\n  ss:\n    taskfile: ./Taskfile.ss.yml\n")
    result = _run_install(target)
    assert "already references Taskfile.ss.yml" in result.stdout


def test_a_target_that_does_not_exist_is_an_error(tmp_path):
    result = _run_install(tmp_path / "missing")
    assert result.returncode == 1
    assert "does not exist" in result.stdout


# ── the pin ──────────────────────────────────────────────────────


def test_a_repo_without_a_pin_gets_this_cli_task_and_node(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    text = (target / "mise.toml").read_text()
    assert _read_pin(target) == __version__
    assert '"task" = "3"' in text
    assert '"node" = "20"' in text


def test_an_existing_pin_is_never_moved_and_a_different_one_is_named(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "mise.toml").write_text('[tools]\n"pipx:slopstopper-cli" = "0.5.0"\n"node" = "18"\n')
    result = _run_install(target)
    assert result.returncode == 0
    text = (target / "mise.toml").read_text()
    assert _read_pin(target) == "0.5.0"
    assert text.count("pipx:slopstopper-cli") == 1
    assert '"node" = "18"' in text and '"node" = "20"' not in text
    assert '"task" = "3"' in text
    assert f"The pin in mise.toml is 0.5.0, but slopstopper-cli {__version__} wrote this suite." in result.stdout
    assert "mise exec -- slopstopper install" in result.stdout


def test_a_matching_pin_gets_no_warning(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target)
    assert "wrote this suite." not in result.stdout.replace(f"slopstopper-cli {__version__} wrote this suite;", "")


def test_a_tools_header_without_a_trailing_newline_still_takes_the_pin(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "mise.toml").write_text("[tools]")
    assert _run_install(target).returncode == 0
    assert _read_pin(target) == __version__


def test_a_node_version_file_suppresses_the_node_seed(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".node-version").write_text("18\n")
    assert _run_install(target).returncode == 0
    assert '"node"' not in (target / "mise.toml").read_text()


def test_an_existing_mise_config_name_is_reused(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".mise.toml").write_text('[tools]\n"python" = "3.12"\n')
    assert _run_install(target).returncode == 0
    assert not (target / "mise.toml").exists()
    text = (target / ".mise.toml").read_text()
    assert '"python" = "3.12"' in text and "pipx:slopstopper-cli" in text


def test_a_legacy_cli_version_migrates_into_the_pin_and_is_stripped(tmp_path):
    target = _make_minimal_target(tmp_path)
    cfg = target / ".slopstopper.yml"
    cfg.write_text(
        "smoke:\n  og_image_path: /og-image.png\n"
        "# ── slopstopper-cli version pin ──\n# blurb\ncli_version: '0.5.0'\n"
        "# ── Node version pin ──\n# blurb\nnode_version: '22'\n"
        "headers:\n  source: public/_headers\n"
    )
    assert _run_install(target).returncode == 0
    assert _read_pin(target) == "0.5.0"
    text = cfg.read_text()
    assert "cli_version" not in text and "node_version" not in text
    assert "version pin" not in text
    assert "og_image_path: /og-image.png" in text and "source: public/_headers" in text
    assert '"node" = "20"' in (target / "mise.toml").read_text()


# ── workflows, the marker and the profile ────────────────────────


def test_stale_marker_with_zero_workflows_on_disk_is_ignored(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "openapi.yaml").write_text("openapi: 3.0.0\n")
    (target / ".ss").mkdir()
    names = sorted(n for n in suite.GENERIC_WORKFLOWS if n.endswith(".yml") and n != "ss-cloudflare-deployed.yml")
    (target / ".ss/.workflows-installed").write_text("\n".join(names) + "\n")
    result = _run_install(target)
    assert result.returncode == 0, result.stderr
    assert _installed(target) == set(names)
    assert "stale" in result.stdout.lower()


def test_a_deleted_workflow_stays_deleted_until_its_marker_line_goes(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    deleted = target / ".github/workflows/ss-security-secrets-check.yml"
    deleted.unlink()
    for _ in range(2):
        result = _run_install(target)
        assert result.returncode == 0, result.stderr
        assert not deleted.exists()
        assert "stale" not in result.stdout.lower()
        assert "1 previously-deleted skipped" in result.stdout
    marker = target / ".ss/.workflows-installed"
    assert "ss-security-secrets-check.yml" in marker.read_text().split()
    marker.write_text(marker.read_text().replace("ss-security-secrets-check.yml\n", ""))
    assert _run_install(target).returncode == 0
    assert deleted.exists()


API_DROPPED = {
    "ss-reliability-smoke-tests.yml",
    "ss-reliability-accessibility-check.yml",
    "ss-reliability-broken-links-check.yml",
    "ss-reliability-core-web-vitals.yml",
    "ss-reliability-seo-check.yml",
    "ss-reliability-llms-txt-check.yml",
    "ss-reliability-robots-txt-check.yml",
    "ss-reliability-sitemap-check.yml",
}
API_WORKFLOWS = {"ss-reliability-api-health-check.yml", "ss-security-api-headers-check.yml"}


def test_profile_flag_writes_the_key_and_drops_those_workflows(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--profile", "api"])
    assert result.returncode == 0, result.stderr
    assert _profile_key(target) == "api"
    installed = _installed(target)
    assert not (installed & API_DROPPED)
    assert "ss-security-sast-check.yml" in installed
    assert "ss-security-dast-check.yml" in installed
    assert not (set((target / ".ss/.workflows-installed").read_text().split()) & API_DROPPED)


def test_profile_env_var_is_equivalent_to_the_flag(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, env_extra={"SLOPSTOPPER_PROFILE": "api"}).returncode == 0
    assert _profile_key(target) == "api"
    assert not (_installed(target) & API_DROPPED)


def test_ui_profile_leaves_out_api_checks_when_there_is_no_api(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target)
    assert result.returncode == 0
    assert not (_installed(target) & API_WORKFLOWS)
    assert "No API found" in result.stdout
    assert "ss-reliability-smoke-tests.yml" in _installed(target)


@pytest.mark.parametrize(
    "marker,body",
    [("openapi.yaml", "openapi: 3.0.0\n"), ("package.json", '{"dependencies": {"express": "^4"}}\n')],
)
def test_ui_profile_keeps_api_checks_when_the_repo_has_an_api(tmp_path, marker, body):
    target = _make_minimal_target(tmp_path)
    (target / marker).write_text(body)
    result = _run_install(target)
    assert result.returncode == 0
    assert API_WORKFLOWS <= _installed(target)
    assert "No API found" not in result.stdout


def test_configuring_api_and_rerunning_adds_the_api_checks(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    assert not (_installed(target) & API_WORKFLOWS)
    cfg = target / ".slopstopper.yml"
    cfg.write_text(cfg.read_text() + "\napi:\n  health:\n    path: /healthz\n")
    assert _run_install(target).returncode == 0
    assert API_WORKFLOWS <= _installed(target)


def test_library_profile_drops_the_api_checks(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "library"]).returncode == 0
    assert not (_installed(target) & API_WORKFLOWS)


def test_switching_profile_removes_and_restores_workflows(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    full = _installed(target)
    assert API_DROPPED <= full
    assert _run_install(target, args=["--profile", "api"]).returncode == 0
    assert not (_installed(target) & API_DROPPED)
    assert _run_install(target, args=["--profile", "ui"]).returncode == 0
    assert _installed(target) == full


def test_plain_rerun_honours_the_stored_profile(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "api"]).returncode == 0
    result = _run_install(target)
    assert result.returncode == 0, result.stderr
    assert _profile_key(target) == "api"
    assert not (_installed(target) & API_DROPPED)


def test_workflows_enabled_keeps_one_check_the_profile_drops(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "api"]).returncode == 0
    config = target / ".slopstopper.yml"
    config.write_text(config.read_text().replace("  enabled: []", "  enabled: [ss-reliability-seo-check.yml]"))
    assert _run_install(target).returncode == 0
    installed = _installed(target)
    assert "ss-reliability-seo-check.yml" in installed
    assert "ss-reliability-core-web-vitals.yml" not in installed


def test_a_disabled_workflow_outside_the_shipped_set_is_swept(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    stray = target / ".github/workflows/ss-old-check.yml"
    stray.write_text("name: old\n")
    cfg = target / ".slopstopper.yml"
    cfg.write_text(cfg.read_text().replace("  disabled: []", "  disabled: [ss-old-check.yml]"))
    result = _run_install(target)
    assert not stray.exists()
    assert "Removed 1 further workflow(s)" in result.stdout


def test_profile_key_is_appended_to_a_config_that_predates_it(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".slopstopper.yml").write_text("urls:\n  production: https://example.com\n")
    assert _run_install(target, args=["--profile", "library"]).returncode == 0
    body = (target / ".slopstopper.yml").read_text()
    assert _profile_key(target) == "library"
    assert "https://example.com" in body


def test_unknown_profile_name_fails_before_touching_the_target(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--profile", "rest"])
    assert result.returncode == 1
    assert "Unknown --profile" in result.stdout
    assert not (target / ".github/workflows").exists()


def test_no_profile_flag_leaves_an_existing_install_unchanged(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".slopstopper.yml").write_text("urls:\n  production:\n")
    assert _run_install(target).returncode == 0
    assert _profile_key(target) is None
    assert API_DROPPED <= _installed(target)


def test_no_task_leaves_no_task_invocation_in_any_workflow(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--no-task", "--no-hooks", "--no-skills"])
    assert result.returncode == 0, result.stderr
    workflows = target / ".github" / "workflows"
    leftovers = {
        p.name: line.strip()
        for p in workflows.glob("ss-*.yml")
        for line in p.read_text().splitlines()
        if "task ss:" in line or "task -x ss:" in line
    }
    assert not leftovers, leftovers
    assert "slopstopper run security:sast" in (workflows / "ss-security-sast-check.yml").read_text()
    assert "Installed in --no-task mode" in result.stdout


def test_the_cloudflare_deploy_trigger_ships_only_to_a_cloudflare_repo(tmp_path):
    target = _make_minimal_target(tmp_path)
    plain = _run_install(target)
    assert "ss-cloudflare-deployed.yml" not in _installed(target)
    assert "Cloudflare" not in plain.stdout and "urls.production" in plain.stdout
    (target / "wrangler.jsonc").write_text('{"name": "site"}\n')
    with_cf = _run_install(target)
    assert "ss-cloudflare-deployed.yml" in _installed(target)
    assert "Cloudflare config detected" in with_cf.stdout
    (target / "wrangler.jsonc").unlink()
    assert _run_install(target).returncode == 0
    assert "ss-cloudflare-deployed.yml" not in _installed(target)
    (target / "website").mkdir()
    (target / "website" / "wrangler.jsonc").write_text('{"name": "site"}\n')
    assert _run_install(target).returncode == 0
    assert "ss-cloudflare-deployed.yml" in _installed(target)


# ── composite actions ────────────────────────────────────────────


@pytest.mark.parametrize("profile", ["ui", "api", "library"])
def test_composite_actions_land_under_every_profile(tmp_path, profile):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", profile, "--no-hooks", "--no-skills"]).returncode == 0
    for action in ("ss-setup", "ss-resolve-url", "ss-playwright"):
        assert (target / ".github/actions" / action / "action.yml").is_file(), action
    assert "ss-setup" not in (target / ".ss/.workflows-installed").read_text()


def test_composite_actions_are_refreshed_not_respected_as_deletions(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    action = target / ".github/actions/ss-setup/action.yml"
    action.write_text("# hand-edited\n")
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    assert "using: composite" in action.read_text()


# ── seeds ────────────────────────────────────────────────────────


def test_seeds_the_dependency_review_allowlist_and_keeps_an_existing_one(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    config = target / ".github" / "dependency-review-config.yml"
    assert "allow-licenses:" in config.read_text()
    config.write_text("allow-licenses:\n  - MIT\n")
    assert _run_install(target).returncode == 0
    assert config.read_text() == "allow-licenses:\n  - MIT\n"


def test_seeds_headers_block_when_public_headers_missing(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    headers = (target / "public/_headers").read_text()
    assert "# slopstopper security headers begin" in headers
    assert "# slopstopper security headers end" in headers


def test_appends_headers_block_to_existing_cache_only_headers_once(tmp_path):
    target = _make_minimal_target(tmp_path)
    existing = "/*.html\n  Cache-Control: public, max-age=0, must-revalidate\n"
    (target / "public/_headers").write_text(existing)
    assert _run_install(target).returncode == 0
    first = (target / "public/_headers").read_text()
    assert existing in first
    assert first.count("# slopstopper security headers begin") == 1
    assert _run_install(target).returncode == 0
    assert (target / "public/_headers").read_text() == first


def test_leaves_a_configured_headers_file_alone(tmp_path):
    target = _make_minimal_target(tmp_path)
    existing = "/*\n  Content-Security-Policy: default-src 'self'\n  Cache-Control: public, max-age=0\n"
    (target / "public/_headers").write_text(existing)
    result = _run_install(target)
    assert (target / "public/_headers").read_text() == existing
    assert "already sets security headers" in result.stdout


def test_a_commented_security_header_does_not_count_as_configured(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "public/_headers").write_text("/*\n  # Content-Security-Policy: default-src 'self'\n  Cache-Control: public, max-age=0\n")
    assert _run_install(target).returncode == 0
    assert "# slopstopper security headers begin" in (target / "public/_headers").read_text()


def test_no_public_directory_means_no_headers_file(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--no-hooks", "--no-skills"])
    assert result.returncode == 0, result.stderr
    assert not (target / "public").exists()
    assert "no public/ directory" in result.stdout


def test_first_install_seeds_the_starter_and_a_rerun_leaves_it_byte_for_byte(tmp_path):
    target = _make_minimal_target(tmp_path)
    cfg = target / ".slopstopper.yml"
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    assert cfg.read_text() == STARTER.read_text() != EXAMPLE.read_text()
    cfg.write_text(cfg.read_text() + "# a note the adopter added\n")
    before = cfg.read_text()
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    assert cfg.read_text() == before


def test_profile_flag_writes_into_the_seeded_starter(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "api", "--no-hooks", "--no-skills"]).returncode == 0
    lines = (target / ".slopstopper.yml").read_text().splitlines()
    assert lines.count("profile: api") == 1
    assert "profile: ui" not in lines


def test_a_pre_015_docs_index_is_named_not_seeded_over(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "docs").mkdir()
    (target / "docs" / "index.md").write_text("# map\n")
    result = _run_install(target, args=["--no-hooks", "--no-skills"])
    assert not (target / "docs" / "README.md").exists()
    assert "git mv docs/index.md docs/README.md" in result.stdout


# ── legacy run-time copies under .ss/ ────────────────────────────


def test_unmodified_spec_copies_are_scrubbed_one_by_one(tmp_path):
    target = _make_minimal_target(tmp_path)
    tests = target / ".ss" / "tests"
    tests.mkdir(parents=True)
    shutil.copy(DATA_DIR / "tests" / "smoke.spec.ts", tests / "smoke.spec.ts")
    shutil.copy(DATA_DIR / "playwright.config.js", target / ".ss" / "playwright.config.js")
    (tests / "e2e.spec.ts").write_text("// customised journeys\n")
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    assert not (tests / "smoke.spec.ts").exists()
    assert not (target / ".ss" / "playwright.config.js").exists()
    assert (tests / "e2e.spec.ts").read_text() == "// customised journeys\n"


def test_a_tests_dir_of_only_unmodified_copies_is_removed(tmp_path):
    target = _make_minimal_target(tmp_path)
    tests = target / ".ss" / "tests"
    tests.mkdir(parents=True)
    shutil.copy(DATA_DIR / "tests" / "accessibility.spec.ts", tests / "accessibility.spec.ts")
    (target / ".ss" / "scripts").mkdir()
    (target / ".ss" / "scripts" / "old.py").write_text("print()\n")
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    assert not tests.exists()
    assert not (target / ".ss" / "scripts").exists()


# ── package.json and .gitignore ──────────────────────────────────


def test_a_repo_without_package_json_gets_a_minimal_one_of_its_own(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    raw = (target / "package.json").read_text()
    pkg = json.loads(raw)
    assert pkg["name"] == "adopter"
    assert pkg["private"] is True
    assert "@playwright/test" in pkg["devDependencies"]
    assert "scripts" not in pkg
    assert "slopstopper" not in raw.lower() and "cloudflare" not in raw.lower()


def test_dev_dependencies_merge_into_an_existing_package_json_and_the_adopters_version_wins(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "package.json").write_text(json.dumps({
        "name": "site", "author": "José", "scripts": {"build": "vite build"},
        "devDependencies": {"@playwright/test": "^1.0.0", "vite": "^5"},
    }, indent=2, ensure_ascii=False) + "\n")
    result = _run_install(target, args=["--no-hooks", "--no-skills"])
    assert result.returncode == 0, result.stderr
    raw = (target / "package.json").read_text()
    pkg = json.loads(raw)
    assert pkg["scripts"] == {"build": "vite build"}
    assert pkg["devDependencies"]["@playwright/test"] == "^1.0.0"
    assert pkg["devDependencies"]["vite"] == "^5"
    assert "@lhci/cli" in pkg["devDependencies"]
    assert "José" in raw
    assert "Added devDependencies" in result.stdout
    assert "Version conflicts (your version kept): @playwright/test" in result.stdout
    second = _run_install(target, args=["--no-hooks", "--no-skills"])
    assert "No new devDependencies to add" in second.stdout
    assert (target / "package.json").read_text() == raw


def test_gitignore_block_covers_the_run_dir_and_node_modules(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    lines = (target / ".gitignore").read_text().splitlines()
    assert ".ss/.run/" in lines and "node_modules/" in lines


OLD_GITIGNORE_BLOCK = "# slopstopper begin\n**/.ss/reports/\nplaywright-report/\n# slopstopper end\n"


def test_refresh_replaces_an_old_gitignore_block_and_keeps_adopter_lines(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".gitignore").write_text("dist/\n.env\n\n" + OLD_GITIGNORE_BLOCK + "\n# mine\ncoverage/\n")
    result = _run_install(target, args=["--no-hooks", "--no-skills"])
    assert "slopstopper block updated" in result.stdout
    template = (REPO_ROOT / "templates" / "gitignore.block").read_text()
    assert (target / ".gitignore").read_text() == "dist/\n.env\n\n" + template + "\n# mine\ncoverage/\n"


def test_a_current_gitignore_block_is_left_byte_identical(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    before = (target / ".gitignore").read_text()
    result = _run_install(target, args=["--no-hooks", "--no-skills"])
    assert "slopstopper block already current" in result.stdout
    assert (target / ".gitignore").read_text() == before


@pytest.mark.parametrize(
    "hand_edited,message",
    [
        ("# slopstopper begin\n.lighthouseci/\nsecrets.txt\n", "has no '# slopstopper end'"),
        ("node_modules/\n# see the # slopstopper begin marker below, once added\n", "no line that is exactly that marker"),
    ],
)
def test_a_hand_edited_gitignore_block_is_left_alone(tmp_path, hand_edited, message):
    target = _make_minimal_target(tmp_path)
    (target / ".gitignore").write_text(hand_edited)
    result = _run_install(target, args=["--no-hooks", "--no-skills"])
    assert message in result.stdout
    assert (target / ".gitignore").read_text() == hand_edited


# ── skills ───────────────────────────────────────────────────────


def test_skills_install_with_every_linked_reference_and_nothing_else(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--no-hooks"])
    assert result.returncode == 0, result.stderr
    for skill in ("slopstopper-install", "slopstopper-triage"):
        skill_md = target / ".claude/skills" / skill / "SKILL.md"
        text = skill_md.read_text()
        assert text.startswith("---\n")
        refs = set(re.findall(r"references/([A-Za-z0-9_.-]+\.md)", text))
        assert refs, skill
        on_disk = {p.name for p in (target / ".claude/skills" / skill / "references").iterdir()}
        assert on_disk == refs, skill
    assert "slopstopper-install: installed" in result.stdout


def test_only_skills_writes_the_skills_and_nothing_else(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--only", "skills"])
    assert result.returncode == 0, result.stderr
    assert (target / ".claude/skills/slopstopper-install/SKILL.md").is_file()
    assert (target / ".claude/skills/slopstopper-triage/references/reproduce.md").is_file()
    for untouched in ("Taskfile.ss.yml", "mise.toml", ".github", ".githooks", ".slopstopper.yml", "package.json"):
        assert not (target / untouched).exists(), untouched
    assert "Installation complete" not in result.stdout
    second = _run_install(target, args=["--only", "skills"])
    assert "slopstopper-install: already up to date" in second.stdout


def test_skills_are_refreshed_as_a_whole_directory(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-hooks"]).returncode == 0
    stray = target / ".claude/skills/slopstopper-install/references/stale.md"
    stray.write_text("# left over from an older skill\n")
    for obsolete in ("install-slopstopper", "slopstopper-update"):
        (target / ".claude/skills" / obsolete).mkdir()
    second = _run_install(target, args=["--no-hooks"])
    assert second.returncode == 0, second.stderr
    assert not stray.exists()
    assert "slopstopper-install: refreshed" in second.stdout
    assert not (target / ".claude/skills/install-slopstopper").exists()
    assert "Removed obsolete skill: slopstopper-update" in second.stdout
    third = _run_install(target, args=["--no-hooks"])
    assert "slopstopper-install: already up to date" in third.stdout


def test_an_interrupted_swap_is_recovered_and_nothing_is_staged_beside_the_skills(tmp_path):
    target = _make_minimal_target(tmp_path)
    skills = target / ".claude/skills"
    stranded = skills / "slopstopper-install.outgoing.123"
    (stranded / "references").mkdir(parents=True)
    (stranded / "SKILL.md").write_text("---\nname: old\n---\n")
    (skills / "slopstopper-triage.incoming.999").mkdir()
    result = _run_install(target, args=["--no-hooks"])
    assert result.returncode == 0, result.stderr
    assert {p.name for p in skills.iterdir()} == {"slopstopper-install", "slopstopper-triage"}
    assert "slopstopper-install: refreshed" in result.stdout
    assert not list((target / ".ss").glob(".skill-*"))


def test_installed_skill_directories_follow_the_umask(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = subprocess.run(
        ["bash", "-c", f"umask 022; {sys.executable} -m slopstopper install --no-hooks {target}"],
        capture_output=True, text=True, env={**os.environ, "SLOPSTOPPER_NO_TOPIC": "1"}, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    for path in (target / ".claude/skills/slopstopper-install", target / ".claude/skills/slopstopper-install/references"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o755, path


def test_no_skills_flag_and_env_var_skip_them(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-skills"]).returncode == 0
    assert not (target / ".claude").exists()
    assert _run_install(target, env_extra={"SLOPSTOPPER_NO_SKILLS": "1"}).returncode == 0
    assert not (target / ".claude").exists()


# ── the pre-push hook ────────────────────────────────────────────


def _hooks_path(target: Path) -> str | None:
    result = subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"], cwd=target, capture_output=True, text=True)
    return result.stdout.strip() or None


def test_installs_pre_push_hook_and_wires_hookspath(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    hook = target / ".githooks/pre-push"
    assert os.access(hook, os.X_OK)
    assert "ss:hygiene:test" in hook.read_text()
    assert _hooks_path(target) == ".githooks"


def test_no_hooks_flag_and_env_var_skip_the_hook(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-hooks"]).returncode == 0
    assert not (target / ".githooks/pre-push").exists()
    assert _run_install(target, env_extra={"SLOPSTOPPER_NO_HOOKS": "1"}).returncode == 0
    assert not (target / ".githooks/pre-push").exists()
    assert _hooks_path(target) is None


def test_existing_hook_manager_preserves_hookspath(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".pre-commit-config.yaml").write_text("repos: []\n")
    result = _run_install(target)
    assert (target / ".githooks/pre-push").exists()
    assert _hooks_path(target) is None
    assert "git config core.hooksPath .githooks" in result.stdout


def test_custom_hookspath_is_not_overridden(tmp_path):
    target = _make_minimal_target(tmp_path)
    subprocess.run(["git", "config", "core.hooksPath", ".my-hooks"], cwd=target, check=True)
    assert _run_install(target).returncode == 0
    assert _hooks_path(target) == ".my-hooks"


def test_a_machine_without_git_or_node_still_completes(tmp_path):
    target = _make_minimal_target(tmp_path)
    empty = tmp_path / "empty-path"
    empty.mkdir()
    result = _run_install(target, env_extra={"PATH": str(empty)})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "git not found" in result.stdout
    assert not (target / ".githooks").exists()
    assert "node (Playwright" in result.stdout
    assert (target / "Taskfile.ss.yml").is_file()


def test_a_target_that_is_not_a_git_repo_gets_no_hook(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--no-skills"])
    assert result.returncode == 0, result.stderr
    assert not (target / ".githooks").exists()
    assert "not a git repository" in result.stdout


# ── the `slopstopper` repo topic ─────────────────────────────────


def _fake_gh_on_path(tmp_path: Path, topics: str | None, *, edit_ok: bool = True) -> dict[str, str]:
    """A `gh` stub first on PATH that logs every call. Never the real gh: a
    test must not edit a real repository."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "gh-calls.log"
    stub = bin_dir / "gh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f"echo \"$*\" >> '{log}'\n"
        "case \"$1 $2\" in\n"
        + (f"  'repo view') printf '%s' '{topics}'; exit 0 ;;\n" if topics is not None else "  'repo view') exit 1 ;;\n")
        + ("  'repo edit') exit 0 ;;\n" if edit_ok else "  'repo edit') exit 1 ;;\n")
        + "  'workflow list') echo '[]'; exit 0 ;;\n"
        "esac\n"
        "exit 1\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "SLOPSTOPPER_NO_TOPIC": None}


def _gh_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "gh-calls.log"
    return log.read_text().splitlines() if log.exists() else []


def test_install_adds_the_slopstopper_repo_topic_when_gh_can_reach_the_repo(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--no-hooks", "--no-skills"], env_extra=_fake_gh_on_path(tmp_path, ""))
    assert result.returncode == 0, result.stderr
    assert "repo edit --add-topic slopstopper" in _gh_calls(tmp_path)
    assert "Repo topic 'slopstopper' added" in result.stdout


def test_install_leaves_an_existing_topic_alone(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--no-hooks", "--no-skills"], env_extra=_fake_gh_on_path(tmp_path, "python\nslopstopper\n"))
    assert result.returncode == 0, result.stderr
    assert not [c for c in _gh_calls(tmp_path) if c.startswith("repo edit")]
    assert "Repo topic 'slopstopper' already set" in result.stdout


def test_no_topic_flag_skips_gh_entirely(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--no-hooks", "--no-skills", "--no-topic"], env_extra=_fake_gh_on_path(tmp_path, ""))
    assert result.returncode == 0, result.stderr
    assert not [c for c in _gh_calls(tmp_path) if c.startswith("repo")]
    assert "Repo topic" not in result.stdout


def test_install_says_how_to_add_the_topic_when_gh_cannot_reach_the_repo(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--no-hooks", "--no-skills"], env_extra=_fake_gh_on_path(tmp_path, None))
    assert result.returncode == 0, result.stderr
    assert "gh can't reach this repo" in result.stdout
    assert "gh repo edit --add-topic slopstopper" in result.stdout


def test_install_says_topics_need_admin_when_gh_sees_the_repo_but_cannot_edit_it(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--no-hooks", "--no-skills"], env_extra=_fake_gh_on_path(tmp_path, "", edit_ok=False))
    assert result.returncode == 0, result.stderr
    assert "repo edit --add-topic slopstopper" in _gh_calls(tmp_path)
    assert "topics need admin" in result.stdout
