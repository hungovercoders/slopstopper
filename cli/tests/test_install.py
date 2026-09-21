"""Integration tests for install.sh.

install.sh is bash, not Python — but it's CLI-adjacent (the entry point
adopters run) and these tests exercise install.sh in a subprocess
against a throwaway target dir so the deletion-tracking, pipx-version
and security-headers fixes don't regress.

Each test resolves install.sh from the repo root (parent of cli/) and
runs it as `bash install.sh <target>`, which short-circuits the
GitHub clone path because SCRIPT_DIR != TARGET and templates/ +
install.sh both live next to the script.

SKIP_CLI_INSTALL=1 makes install.sh write the mise.toml pin offline
(no `mise` binary, no PyPI) so these assert on the bash-side pin logic
deterministically, without performing the real mise install.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SH = REPO_ROOT / "install.sh"


def _run_install(
    target: Path,
    *,
    args: list[str] | None = None,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run install.sh against the given target dir. Returns the completed process.

    Always sets SKIP_CLI_INSTALL=1 so tests don't install from PyPI via mise
    on every invocation — these tests exercise the bash-side behaviour
    (workflow tracking, headers seeding, mise.toml pinning), not the CLI
    install itself. Extra flags (e.g. ["--upgrade-cli"]) go before the
    target via `args`.
    """
    env = os.environ.copy()
    env["SKIP_CLI_INSTALL"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(INSTALL_SH), *(args or []), str(target)],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


def _read_pin(target: Path) -> str | None:
    """Return the slopstopper-cli version pinned in the target's mise.toml
    (the [tools] "pipx:slopstopper-cli" entry), or None if absent. Mirrors the
    sed parse install.sh uses and the entry jdx/mise-action reads in CI."""
    cfg = target / "mise.toml"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        if "pipx:slopstopper-cli" in line and "=" in line:
            value = line.split("=", 1)[1].strip().strip("'\"")
            return value or None
    return None


def _read_legacy_pin(target: Path) -> str | None:
    """Return the legacy cli_version from .slopstopper.yml, or None if absent."""
    cfg = target / ".slopstopper.yml"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        if line.startswith("cli_version:"):
            value = line.split(":", 1)[1].strip().strip("'\"")
            return value or None
    return None


# ── mise.toml CLI pin ────────────────────────────────────────────


def test_cli_version_flag_writes_exact_pin(tmp_path):
    """--cli-version X.Y.Z records that exact version in mise.toml."""
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _read_pin(target) == "9.9.9"


def test_task_is_pinned_alongside_cli(tmp_path):
    """mise.toml also pins `task` so mise installs the canonical interface."""
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert '"task" = "3"' in (target / "mise.toml").read_text()


def test_first_install_records_latest_as_pin(tmp_path):
    """A first install with no pin set records the latest published version."""
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, env_extra={"SLOPSTOPPER_FORCE_LATEST": "1.2.3"})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _read_pin(target) == "1.2.3"


def test_plain_refresh_leaves_pin_untouched(tmp_path):
    """A plain re-run must not move an existing pin (no surprise upgrades)."""
    target = _make_minimal_target(tmp_path)
    first = _run_install(target, args=["--cli-version", "0.5.0"])
    assert first.returncode == 0, f"{first.stdout}\n{first.stderr}"
    assert _read_pin(target) == "0.5.0"

    # Re-run with a NEWER latest available — the pin must still hold.
    second = _run_install(target, env_extra={"SLOPSTOPPER_FORCE_LATEST": "2.0.0"})
    assert second.returncode == 0, f"{second.stdout}\n{second.stderr}"
    assert _read_pin(target) == "0.5.0"
    assert (target / "mise.toml").read_text().count("pipx:slopstopper-cli") == 1


def test_upgrade_cli_flag_bumps_pin_to_latest(tmp_path):
    """--upgrade-cli rewrites the pin to the latest published version."""
    target = _make_minimal_target(tmp_path)
    first = _run_install(target, args=["--cli-version", "0.5.0"])
    assert first.returncode == 0, f"{first.stdout}\n{first.stderr}"

    second = _run_install(
        target,
        args=["--upgrade-cli"],
        env_extra={"SLOPSTOPPER_FORCE_LATEST": "2.0.0"},
    )
    assert second.returncode == 0, f"{second.stdout}\n{second.stderr}"
    assert _read_pin(target) == "2.0.0"
    assert (target / "mise.toml").read_text().count("pipx:slopstopper-cli") == 1


def test_legacy_cli_version_migrates_and_strips(tmp_path):
    """A pre-mise cli_version in .slopstopper.yml migrates into mise.toml and
    the dead key is stripped, leaving other config keys untouched."""
    target = _make_minimal_target(tmp_path)
    cfg = target / ".slopstopper.yml"
    cfg.write_text(
        "smoke:\n"
        "  og_image_path: /og-image.png\n"
        "# ── slopstopper-cli version pin ──\n"
        "# blurb\n"
        "cli_version: '0.5.0'\n"
        "headers:\n"
        "  source: public/_headers\n"
    )

    # Plain refresh (no flags): the pin should migrate from .slopstopper.yml,
    # NOT bump to the newer "latest".
    result = _run_install(target, env_extra={"SLOPSTOPPER_FORCE_LATEST": "2.0.0"})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    assert _read_pin(target) == "0.5.0"          # migrated into mise.toml
    assert _read_legacy_pin(target) is None       # cli_version key stripped
    text = cfg.read_text()
    assert "og_image_path: /og-image.png" in text  # other keys preserved
    assert "source: public/_headers" in text


def test_existing_mise_tools_are_preserved(tmp_path):
    """Writing the CLI pin must not disturb other tools in an existing mise.toml."""
    target = _make_minimal_target(tmp_path)
    (target / "mise.toml").write_text('[tools]\n"node" = "20"\n')

    result = _run_install(target, args=["--cli-version", "3.3.3"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    text = (target / "mise.toml").read_text()
    assert _read_pin(target) == "3.3.3"
    assert '"node" = "20"' in text


def test_node_is_seeded_when_absent(tmp_path):
    """A fresh install seeds a default node pin in mise.toml — node is a tool
    version, so it lives in mise (read by CI via jdx/mise-action), not
    .slopstopper.yml."""
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert '"node" = "20"' in (target / "mise.toml").read_text()


def test_existing_node_pin_is_not_overridden(tmp_path):
    """If the adopter already pins node in mise.toml, install leaves it alone."""
    target = _make_minimal_target(tmp_path)
    (target / "mise.toml").write_text('[tools]\n"node" = "18"\n')
    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    text = (target / "mise.toml").read_text()
    assert '"node" = "18"' in text
    assert '"node" = "20"' not in text


def test_node_version_file_suppresses_mise_node_seed(tmp_path):
    """An existing .node-version means the adopter manages node themselves —
    install must not also seed a node pin into mise.toml."""
    target = _make_minimal_target(tmp_path)
    (target / ".node-version").write_text("18\n")
    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert '"node"' not in (target / "mise.toml").read_text()


def test_legacy_node_version_is_stripped(tmp_path):
    """A dead node_version in .slopstopper.yml (and its comment block) is removed
    on refresh — it was never read; node lives in mise.toml now."""
    target = _make_minimal_target(tmp_path)
    cfg = target / ".slopstopper.yml"
    cfg.write_text(
        "# ── Node version pin ──\n"
        "# blurb\n"
        "node_version: '22'\n"
        "headers:\n"
        "  source: public/_headers\n"
    )
    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    text = cfg.read_text()
    assert "node_version" not in text                # dead key stripped
    assert "# ── Node version pin" not in text        # comment block stripped too
    assert "source: public/_headers" in text          # other keys preserved
    # Not migrated — the freshly-seeded mise pin is the default, not the old value.
    assert '"node" = "20"' in (target / "mise.toml").read_text()


def test_legacy_node_version_stripped_but_existing_mise_pin_wins(tmp_path):
    """If the adopter already pins node in mise.toml, the dead node_version key
    is still stripped but the existing mise pin is left untouched."""
    target = _make_minimal_target(tmp_path)
    (target / "mise.toml").write_text('[tools]\n"node" = "18"\n')
    cfg = target / ".slopstopper.yml"
    cfg.write_text("node_version: '22'\nheaders:\n  source: public/_headers\n")

    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    assert "node_version" not in cfg.read_text()
    mise_text = (target / "mise.toml").read_text()
    assert '"node" = "18"' in mise_text
    assert '"node" = "22"' not in mise_text


def test_cli_version_requires_argument(tmp_path):
    """--cli-version with no value is a hard error, not a silent no-op."""
    target = _make_minimal_target(tmp_path)
    result = subprocess.run(
        ["bash", str(INSTALL_SH), "--cli-version"],
        capture_output=True,
        text=True,
        env={**os.environ, "SKIP_CLI_INSTALL": "1"},
        cwd=REPO_ROOT,
    )
    assert result.returncode != 0
    assert "--cli-version requires a version" in (result.stdout + result.stderr)


def _make_minimal_target(tmp_path: Path) -> Path:
    """Create the minimum scaffolding install.sh expects: a git repo with public/."""
    target = tmp_path / "adopter"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    (target / "public").mkdir()
    return target


# ── #100 deletion-tracking false positive on stale marker ────────


def test_stale_marker_with_zero_workflows_on_disk_is_ignored(tmp_path):
    """A marker listing all 20 workflows with no workflows on disk is stale.

    Reproduces the failure mode: prior branch left
    `.ss/.workflows-installed` behind, the install thinks the user
    deleted every workflow and silently installs zero.
    """
    target = _make_minimal_target(tmp_path)

    # Plant a stale marker listing all 20 ss-*.yml workflows, with zero
    # workflows on disk (no .github/workflows/ at all).
    (target / ".ss").mkdir()
    workflow_names = sorted(p.name for p in (REPO_ROOT / ".github/workflows").glob("ss-*.yml"))
    assert len(workflow_names) >= 15, f"Sanity: expected ≥15 ss-*.yml workflows, found {len(workflow_names)}"
    (target / ".ss/.workflows-installed").write_text("\n".join(workflow_names) + "\n")

    result = _run_install(target)
    assert result.returncode == 0, f"install.sh failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    installed = sorted(p.name for p in (target / ".github/workflows").glob("ss-*.yml"))
    assert len(installed) >= len(workflow_names) - 1, (
        f"Expected ≥{len(workflow_names) - 1} workflows installed (allowing for .md gh-aw split), "
        f"got {len(installed)}:\n{installed}\nstdout:\n{result.stdout}"
    )
    # Should also surface the warning so silent fixes aren't silent.
    assert "stale" in result.stdout.lower() or "stale" in result.stderr.lower(), (
        f"Expected 'stale' warning in output:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_genuine_user_deletion_is_still_respected(tmp_path):
    """If some workflows are on disk and others are in the marker but missing,
    respect the deletion — that's a real user choice."""
    target = _make_minimal_target(tmp_path)

    # Run install once to populate the marker + workflows.
    first = _run_install(target)
    assert first.returncode == 0, f"first install failed:\n{first.stdout}\n{first.stderr}"

    # Delete one specific workflow.
    deleted = "ss-security-secrets-check.yml"
    deleted_path = target / ".github/workflows" / deleted
    assert deleted_path.exists(), "test setup: expected the workflow to be present"
    deleted_path.unlink()

    # Re-run install. Marker still lists the deleted workflow; the others remain on disk.
    second = _run_install(target)
    assert second.returncode == 0, f"second install failed:\n{second.stdout}\n{second.stderr}"
    assert not deleted_path.exists(), "user-deleted workflow should NOT be re-added"
    assert "stale" not in second.stdout.lower(), (
        "stale-marker warning should NOT fire when other workflows are on disk"
    )


# ── #102 security-headers idempotent append ──────────────────────


def test_seeds_headers_block_when_public_headers_missing(tmp_path):
    """Fresh adopter, no public/_headers — seeded with the slopstopper block."""
    target = _make_minimal_target(tmp_path)

    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    headers = (target / "public/_headers").read_text()
    assert "# slopstopper security headers begin" in headers
    assert "# slopstopper security headers end" in headers


def test_appends_headers_block_to_existing_cache_only_headers(tmp_path):
    """Adopter has public/_headers with only cache rules — slopstopper appends without losing them."""
    target = _make_minimal_target(tmp_path)
    existing = (
        "/*.html\n"
        "  Cache-Control: public, max-age=0, must-revalidate\n"
        "\n"
        "/assets/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
    )
    (target / "public/_headers").write_text(existing)

    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    headers = (target / "public/_headers").read_text()
    assert existing in headers, "adopter's existing cache rules must be preserved"
    assert "# slopstopper security headers begin" in headers
    assert "# slopstopper security headers end" in headers


def test_headers_append_is_idempotent(tmp_path):
    """Second install should not duplicate the headers block."""
    target = _make_minimal_target(tmp_path)
    existing = "/*.html\n  Cache-Control: public, max-age=0\n"
    (target / "public/_headers").write_text(existing)

    first = _run_install(target)
    assert first.returncode == 0
    first_content = (target / "public/_headers").read_text()
    first_begin_count = first_content.count("# slopstopper security headers begin")
    assert first_begin_count == 1, f"expected exactly 1 begin marker after first install, got {first_begin_count}"

    second = _run_install(target)
    assert second.returncode == 0
    second_content = (target / "public/_headers").read_text()
    second_begin_count = second_content.count("# slopstopper security headers begin")
    assert second_begin_count == 1, f"expected exactly 1 begin marker after second install (idempotent append), got {second_begin_count}"
    assert second_content == first_content, "second install must not modify the headers file"


# ── pre-push hygiene hook ────────────────────────────────────────


def _hooks_path(target: Path) -> str | None:
    """Return the target repo's local core.hooksPath, or None if unset."""
    result = subprocess.run(
        ["git", "config", "--local", "--get", "core.hooksPath"],
        cwd=target,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value or None


def test_installs_pre_push_hook_and_wires_hookspath(tmp_path):
    """Fresh adopter with no existing hook setup — the hook file lands,
    is executable, and core.hooksPath is wired to .githooks."""
    target = _make_minimal_target(tmp_path)

    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    hook = target / ".githooks/pre-push"
    assert hook.exists(), "pre-push hook file should be installed"
    assert os.access(hook, os.X_OK), "pre-push hook must be executable"
    assert "ss:hygiene:test" in hook.read_text(), "hook must run the hygiene aggregate"
    assert _hooks_path(target) == ".githooks", "core.hooksPath should be wired to .githooks"


def test_no_hooks_flag_skips_hook(tmp_path):
    """--no-hooks writes neither the hook file nor the hooksPath config."""
    target = _make_minimal_target(tmp_path)

    result = _run_install(target, args=["--no-hooks"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    assert not (target / ".githooks/pre-push").exists(), "--no-hooks must not write the hook"
    assert _hooks_path(target) is None, "--no-hooks must not touch core.hooksPath"


def test_no_hooks_env_var_skips_hook(tmp_path):
    """SLOPSTOPPER_NO_HOOKS=1 is the env-var equivalent of --no-hooks."""
    target = _make_minimal_target(tmp_path)

    result = _run_install(target, env_extra={"SLOPSTOPPER_NO_HOOKS": "1"})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    assert not (target / ".githooks/pre-push").exists()
    assert _hooks_path(target) is None


def test_existing_hook_manager_preserves_hookspath(tmp_path):
    """An adopter already running pre-commit gets the hook file dropped in,
    but their core.hooksPath is left untouched (never hijack an existing setup)."""
    target = _make_minimal_target(tmp_path)
    (target / ".pre-commit-config.yaml").write_text("repos: []\n")

    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    assert (target / ".githooks/pre-push").exists(), "hook file should still be written for opt-in"
    assert _hooks_path(target) is None, "existing hook manager: core.hooksPath must be left alone"


def test_custom_hookspath_is_not_overridden(tmp_path):
    """A repo that already points core.hooksPath elsewhere keeps its value."""
    target = _make_minimal_target(tmp_path)
    subprocess.run(
        ["git", "config", "core.hooksPath", ".my-hooks"], cwd=target, check=True
    )

    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    assert _hooks_path(target) == ".my-hooks", "custom hooksPath must be preserved"


# ── project-shape profiles ───────────────────────────────────────


def _installed(target: Path) -> set[str]:
    return {p.name for p in (target / ".github/workflows").glob("ss-*.yml")}


def _profile_key(target: Path) -> str | None:
    for line in (target / ".slopstopper.yml").read_text().splitlines():
        if line.startswith("profile:"):
            return line.split(":", 1)[1].strip()
    return None


# The nine workflows the `api` profile drops. Hardcoded
# rather than read from profiles.json, so a change to the mapping has to
# be made deliberately in both places.
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


def test_profile_flag_writes_the_key_and_drops_those_workflows(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--profile", "api"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    assert _profile_key(target) == "api"
    installed = _installed(target)
    assert not (installed & API_DROPPED), f"api profile installed browser checks: {installed & API_DROPPED}"
    # The static layer stays in place, and DAST rides along: it scans an
    # API through ZAP's OpenAPI mode and skips until a spec is configured.
    assert "ss-security-sast-check.yml" in installed
    assert "ss-security-dast-check.yml" in installed


def test_profile_env_var_is_equivalent_to_the_flag(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, env_extra={"SLOPSTOPPER_PROFILE": "api"})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _profile_key(target) == "api"
    assert not (_installed(target) & API_DROPPED)


# The two API checks. `library` drops them (nothing served at all); `ui`
# and `api` both keep them, where they stay inert until api.* is configured.
API_WORKFLOWS = {
    "ss-reliability-api-health-check.yml",
    "ss-security-api-headers-check.yml",
}


def test_api_checks_ship_under_the_default_profile(tmp_path):
    """A ui repo keeps them: they're inert until configured, and a repo with
    API routes shouldn't have to find workflows.enabled to get coverage."""
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    assert API_WORKFLOWS <= _installed(target)


def test_api_checks_ship_under_the_api_profile(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "api"]).returncode == 0
    installed = _installed(target)
    assert API_WORKFLOWS <= installed
    assert not (installed & API_DROPPED)


def test_library_profile_drops_the_api_checks(tmp_path):
    """A library serves nothing, so there is no endpoint to probe."""
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "library"]).returncode == 0
    assert not (_installed(target) & API_WORKFLOWS)

def test_profile_dropped_workflows_stay_out_of_the_marker(tmp_path):
    """Otherwise the deletion-respect rule would suppress them forever.

    The marker means "we installed this". A profile-skipped workflow was
    never installed, so recording it would make a later profile change
    look like a user deletion and never bring the workflow back.
    """
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "api"]).returncode == 0
    marker = (target / ".ss/.workflows-installed").read_text().split()
    assert not (set(marker) & API_DROPPED)


def test_switching_profile_removes_and_restores_workflows(tmp_path):
    """ui → api removes the eight; api → ui brings them back."""
    target = _make_minimal_target(tmp_path)
    assert _run_install(target).returncode == 0
    full = _installed(target)
    assert API_DROPPED <= full, "sanity: a default install carries the browser checks"

    assert _run_install(target, args=["--profile", "api"]).returncode == 0
    assert not (_installed(target) & API_DROPPED)

    assert _run_install(target, args=["--profile", "ui"]).returncode == 0
    assert _installed(target) == full


def test_plain_rerun_honours_the_stored_profile(tmp_path):
    """The config is the source of truth, not the flag — a bare re-run
    must not resurrect the workflows the stored profile drops."""
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "api"]).returncode == 0

    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _profile_key(target) == "api", "a bare re-run must not rewrite the key"
    assert not (_installed(target) & API_DROPPED)


def test_workflows_enabled_keeps_one_check_the_profile_drops(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--profile", "api"]).returncode == 0

    config = target / ".slopstopper.yml"
    config.write_text(
        config.read_text().replace(
            "  enabled: []", "  enabled: [ss-reliability-seo-check.yml]"
        )
    )
    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    installed = _installed(target)
    assert "ss-reliability-seo-check.yml" in installed
    assert "ss-reliability-core-web-vitals.yml" not in installed


def test_profile_key_is_appended_to_a_config_that_predates_it(tmp_path):
    """An adopter upgrading from a pre-profile release has no such key."""
    target = _make_minimal_target(tmp_path)
    (target / ".slopstopper.yml").write_text("urls:\n  production: https://example.com\n")

    result = _run_install(target, args=["--profile", "library"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    body = (target / ".slopstopper.yml").read_text()
    assert _profile_key(target) == "library"
    assert "https://example.com" in body, "existing config must be preserved"


def test_unknown_profile_name_fails_before_touching_the_target(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--profile", "rest"])
    assert result.returncode != 0
    assert "Unknown --profile" in result.stdout + result.stderr
    assert not (target / ".github/workflows").exists(), "should fail before installing"


def test_no_profile_flag_leaves_an_existing_install_unchanged(tmp_path):
    """The key arriving in the schema must not change an install's shape.

    An unset `profile:` resolves to `ui`, which drops nothing.
    """
    target = _make_minimal_target(tmp_path)
    (target / ".slopstopper.yml").write_text("urls:\n  production:\n")

    result = _run_install(target)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _profile_key(target) is None, "no flag → no key written"
    assert API_DROPPED <= _installed(target)


# When the profiles module cannot be resolved at all (no python3, or an
# unreadable cli/ tree — simulated here by breaking the interpreter), the
# installer must not quietly hand a repo the full `ui` workflow set it
# explicitly opted out of. PYTHONHOME pointing nowhere makes every
# `python3 -c …` in install.sh fail the way a missing interpreter would.
_BROKEN_PYTHON = {"PYTHONHOME": "/nonexistent-python-home"}


def test_unresolvable_profile_aborts_when_the_config_opted_out(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".slopstopper.yml").write_text("profile: api\n")
    result = _run_install(target, env_extra=_BROKEN_PYTHON)
    assert result.returncode != 0
    assert "profile 'api'" in result.stdout + result.stderr
    assert not _installed(target), "must abort before any workflow lands"


def test_unresolvable_profile_warns_and_installs_everything_for_the_default(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, env_extra=_BROKEN_PYTHON)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "defaulting to 'ui'" in result.stdout + result.stderr
    assert "ss-reliability-smoke-tests.yml" in _installed(target)


# ── --no-task rewrites every Task invocation ─────────────────────


def test_no_task_leaves_no_task_invocation_in_any_workflow(tmp_path):
    """`task -x ss:…` (exit-code passthrough) must be rewritten as well as
    `task ss:…` — otherwise --no-task installs still need Task."""
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
    sast = (workflows / "ss-security-sast-check.yml").read_text()
    assert "slopstopper run security:sast" in sast


# ── composite actions ────────────────────────────────────────────
#
# Every ss-* workflow starts with `uses: ./.github/actions/ss-setup`, so
# the actions must land next to the workflows or every check fails on
# its first step. They are plumbing, not checks: copied under every
# profile, refreshed wholesale, never tracked in the marker.


@pytest.mark.parametrize("profile", ["ui", "api", "library"])
def test_composite_actions_land_under_every_profile(tmp_path, profile):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--profile", profile, "--no-hooks", "--no-skills"])
    assert result.returncode == 0, result.stderr
    for action in ("ss-setup", "ss-resolve-url"):
        assert (target / ".github/actions" / action / "action.yml").is_file(), action
    marker = (target / ".ss/.workflows-installed").read_text()
    assert "ss-setup" not in marker


def test_composite_actions_are_refreshed_not_respected_as_deletions(tmp_path):
    """Deleting a workflow is a choice the installer respects; deleting the
    plumbing every workflow needs is not — it comes back."""
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    action = target / ".github/actions/ss-setup/action.yml"
    action.write_text("# hand-edited\n")
    assert _run_install(target, args=["--no-hooks", "--no-skills"]).returncode == 0
    assert "hand-edited" not in action.read_text()
    assert "using: composite" in action.read_text()
