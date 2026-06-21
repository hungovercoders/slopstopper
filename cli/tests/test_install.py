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
