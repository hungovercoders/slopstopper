"""Integration tests for install.sh, the bootstrap.

install.sh pins slopstopper-cli (with task and node) in the target's mise
config, installs that version through mise, and hands over to
`slopstopper install`, which writes the suite (`test_install_cli.py` covers
that). These tests exercise the bash side: the pin, the version notes, and
that the hand-over happens through mise with the flags passed on.

SKIP_CLI_INSTALL=1 makes install.sh write the pin offline (no `mise`
binary, no PyPI) and run whatever `slopstopper` is on PATH, which here is
the editable install the tests run under.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

from slopstopper import __version__

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SH = REPO_ROOT / "install.sh"
VENV_BIN = Path(sys.executable).parent


def _run_install(
    target: Path,
    *,
    args: list[str] | None = None,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["SKIP_CLI_INSTALL"] = "1"
    env["SLOPSTOPPER_NO_TOPIC"] = "1"
    env["PATH"] = f"{VENV_BIN}{os.pathsep}{env['PATH']}"
    if env_extra:
        env.update(env_extra)
    env = {k: v for k, v in env.items() if v is not None}
    return subprocess.run(
        ["bash", str(INSTALL_SH), *(args or []), str(target)],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT,
    )


def _make_minimal_target(tmp_path: Path) -> Path:
    target = tmp_path / "adopter"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    (target / "public").mkdir()
    return target


def _read_pin(target: Path) -> str | None:
    """The slopstopper-cli version pinned in the target's mise.toml, or None."""
    cfg = target / "mise.toml"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        if "pipx:slopstopper-cli" in line and "=" in line:
            return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


def _read_legacy_pin(target: Path) -> str | None:
    cfg = target / ".slopstopper.yml"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        if line.startswith("cli_version:"):
            return line.split(":", 1)[1].strip().strip("'\"") or None
    return None


def _installed(target: Path) -> set[str]:
    return {p.name for p in (target / ".github/workflows").glob("ss-*.yml")}


# ── the hand-over ────────────────────────────────────────────────


def test_a_plain_run_pins_the_cli_and_writes_the_suite(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, env_extra={"SLOPSTOPPER_FORCE_LATEST": __version__})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _read_pin(target) == __version__
    assert (target / "Taskfile.ss.yml").is_file()
    assert "ss-security-sast-check.yml" in _installed(target)
    assert (target / ".ss/.installed-from").read_text() == f"{__version__}\n"
    assert "Installation complete" in result.stdout
    assert "(pinned, latest on PyPI)" in result.stdout


def test_the_cli_flags_pass_through(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--profile", "api", "--no-task", "--no-hooks", "--no-skills", "--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "profile: api" in (target / ".slopstopper.yml").read_text().splitlines()
    assert "ss-reliability-seo-check.yml" not in _installed(target)
    assert "task ss:" not in (target / ".github/workflows/ss-security-sast-check.yml").read_text()
    assert not (target / ".githooks").exists()
    assert not (target / ".claude").exists()


def test_a_refusal_from_the_cli_fails_the_install(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--profile", "rest", "--cli-version", "9.9.9"])
    assert result.returncode == 1
    assert "Unknown --profile 'rest'" in result.stdout
    assert "did not complete" in result.stderr
    assert not (target / ".github/workflows").exists()


def _fake_cli_on_path(tmp_path: Path, version: str) -> dict[str, str]:
    """A `slopstopper` stub printing `version`, first on PATH: what a shell
    with mise activated resolves until the prompt hook re-runs. Its
    `install` records that it ran, so a test can tell it from mise's."""
    bin_dir = tmp_path / "fakebin-cli"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "slopstopper"
    stub.write_text(
        "#!/bin/sh\n"
        f'[ "$1" = install ] && touch "{tmp_path}/ran-through-path"\n'
        f'echo "slopstopper {version}"\n'
    )
    stub.chmod(0o755)
    return {"PATH": f"{bin_dir}{os.pathsep}{VENV_BIN}{os.pathsep}{os.environ['PATH']}"}


def _fake_mise_on_path(tmp_path: Path, *, version: str) -> dict[str, str]:
    """A `mise` stub that stands in for the real install: `use`, `reshim`
    and `which` succeed and do nothing, `exec -- slopstopper` answers
    `--version` with `version` and records an `install`. With
    SKIP_CLI_INSTALL unset the installer takes its real mise path against
    it, offline, so a test can tell a pinned-CLI call from a PATH one."""
    bin_dir = tmp_path / "fakebin-mise"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "mise"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "case \"$1\" in\n"
        "  use|reshim|which) exit 0 ;;\n"
        "  exec) shift; [ \"$1\" = -- ] && shift; shift  # slopstopper\n"
        "    case \"$1\" in\n"
        f"      --version) echo 'slopstopper {version}'; exit 0 ;;\n"
        f"      install) touch '{tmp_path}/ran-through-mise'; exit 0 ;;\n"
        "    esac; exit 1 ;;\n"
        "esac\n"
        "exit 1\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "SKIP_CLI_INSTALL": None, "SLOPSTOPPER_FORCE_LATEST": version}


def test_the_hand_over_goes_through_mise_not_the_shell(tmp_path):
    """After `--upgrade-cli` the shell still resolves the old binary; the
    suite must come from the pinned CLI, which only mise resolves."""
    target = _make_minimal_target(tmp_path)
    env = _fake_cli_on_path(tmp_path, "1.0.0")
    env.update(_fake_mise_on_path(tmp_path, version="2.0.0"))
    env["PATH"] = f"{tmp_path / 'fakebin-mise'}{os.pathsep}{tmp_path / 'fakebin-cli'}{os.pathsep}{os.environ['PATH']}"
    result = _run_install(target, args=["--cli-version", "2.0.0"], env_extra=env)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert (tmp_path / "ran-through-mise").exists()
    assert not (tmp_path / "ran-through-path").exists()
    assert "This shell still runs slopstopper 1.0.0, not the pinned 2.0.0" in result.stdout
    assert "mise exec -- slopstopper" in result.stdout


def test_no_shell_warning_when_shell_resolves_pinned_cli(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--cli-version", "2.0.0"], env_extra=_fake_cli_on_path(tmp_path, "2.0.0"))
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "This shell still runs" not in result.stdout


# ── the pin in mise.toml ─────────────────────────────────────────


def test_cli_version_flag_writes_exact_pin(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, args=["--cli-version", "9.9.9"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _read_pin(target) == "9.9.9"
    assert '"task" = "3"' in (target / "mise.toml").read_text()


def test_first_install_records_latest_as_pin(tmp_path):
    target = _make_minimal_target(tmp_path)
    result = _run_install(target, env_extra={"SLOPSTOPPER_FORCE_LATEST": "1.2.3"})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _read_pin(target) == "1.2.3"


def test_plain_refresh_leaves_pin_untouched(tmp_path):
    """A plain re-run must not move an existing pin (no surprise upgrades)."""
    target = _make_minimal_target(tmp_path)
    first = _run_install(target, args=["--cli-version", "0.5.0"])
    assert first.returncode == 0, f"{first.stdout}\n{first.stderr}"
    second = _run_install(target, env_extra={"SLOPSTOPPER_FORCE_LATEST": "2.0.0"})
    assert second.returncode == 0, f"{second.stdout}\n{second.stderr}"
    assert _read_pin(target) == "0.5.0"
    assert (target / "mise.toml").read_text().count("pipx:slopstopper-cli") == 1
    assert "PyPI latest is 2.0.0" in second.stdout


def test_upgrade_cli_flag_bumps_pin_to_latest(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--cli-version", "0.5.0"]).returncode == 0
    second = _run_install(target, args=["--upgrade-cli"], env_extra={"SLOPSTOPPER_FORCE_LATEST": "2.0.0"})
    assert second.returncode == 0, f"{second.stdout}\n{second.stderr}"
    assert _read_pin(target) == "2.0.0"
    assert (target / "mise.toml").read_text().count("pipx:slopstopper-cli") == 1
    assert "Upgraded 0.5.0 → 2.0.0" in second.stdout


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
    result = _run_install(target, env_extra={"SLOPSTOPPER_FORCE_LATEST": "2.0.0"})
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert _read_pin(target) == "0.5.0"
    assert _read_legacy_pin(target) is None
    text = cfg.read_text()
    assert "og_image_path: /og-image.png" in text
    assert "source: public/_headers" in text


def test_existing_mise_tools_are_preserved(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "mise.toml").write_text('[tools]\n"node" = "20"\n')
    result = _run_install(target, args=["--cli-version", "3.3.3"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    text = (target / "mise.toml").read_text()
    assert _read_pin(target) == "3.3.3"
    assert '"node" = "20"' in text


def test_node_is_seeded_when_absent(tmp_path):
    target = _make_minimal_target(tmp_path)
    assert _run_install(target, args=["--cli-version", "9.9.9"]).returncode == 0
    assert '"node" = "20"' in (target / "mise.toml").read_text()


def test_existing_node_pin_is_not_overridden(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / "mise.toml").write_text('[tools]\n"node" = "18"\n')
    assert _run_install(target, args=["--cli-version", "9.9.9"]).returncode == 0
    text = (target / "mise.toml").read_text()
    assert '"node" = "18"' in text
    assert '"node" = "20"' not in text


def test_node_version_file_suppresses_mise_node_seed(tmp_path):
    target = _make_minimal_target(tmp_path)
    (target / ".node-version").write_text("18\n")
    assert _run_install(target, args=["--cli-version", "9.9.9"]).returncode == 0
    assert '"node"' not in (target / "mise.toml").read_text()


def test_legacy_node_version_is_stripped(tmp_path):
    target = _make_minimal_target(tmp_path)
    cfg = target / ".slopstopper.yml"
    cfg.write_text("# ── Node version pin ──\n# blurb\nnode_version: '22'\nheaders:\n  source: public/_headers\n")
    assert _run_install(target, args=["--cli-version", "9.9.9"]).returncode == 0
    text = cfg.read_text()
    assert "node_version" not in text
    assert "# ── Node version pin" not in text
    assert "source: public/_headers" in text
    assert '"node" = "20"' in (target / "mise.toml").read_text()


def test_cli_version_requires_argument(tmp_path):
    result = subprocess.run(
        ["bash", str(INSTALL_SH), "--cli-version"],
        capture_output=True, text=True, env={**os.environ, "SKIP_CLI_INSTALL": "1"}, cwd=REPO_ROOT,
    )
    assert result.returncode != 0
    assert "--cli-version requires a version" in (result.stdout + result.stderr)


def test_the_bootstrap_needs_no_git_and_no_checkout(tmp_path):
    """The suite comes from the wheel: a bare directory with the CLI on PATH
    is enough, and nothing is cloned."""
    target = tmp_path / "repo"
    target.mkdir()
    result = _run_install(target, args=["--cli-version", "9.9.9", "--no-skills"])
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "Cloning" not in result.stdout
    assert (target / "Taskfile.ss.yml").is_file()


# ── install-skill.sh, the standalone skills refresher ────────────


def _run_install_skill(target, src, umask=None):
    cmd = f'bash "{REPO_ROOT / "install-skill.sh"}" "{target}"'
    if umask is not None:
        cmd = f"umask {umask}; {cmd}"
    return subprocess.run(
        ["bash", "-c", cmd], capture_output=True, text=True,
        env={**os.environ, "SLOPSTOPPER_REPO_RAW": f"file://{src}"},
    )


def _skill_source(tmp_path):
    """A file:// copy of this repo's skills that a test can break."""
    src = tmp_path / "src"
    for skill in ("slopstopper-install", "slopstopper-triage"):
        skill_dir = REPO_ROOT / ".claude/skills" / skill
        dest = src / ".claude/skills" / skill
        (dest / "references").mkdir(parents=True)
        (dest / "SKILL.md").write_text((skill_dir / "SKILL.md").read_text())
        for ref in (skill_dir / "references").glob("*.md"):
            (dest / "references" / ref.name).write_text(ref.read_text())
    return src


def test_install_skill_sh_fetches_skill_md_and_every_linked_reference(tmp_path):
    import re

    target = tmp_path / "adopter"
    target.mkdir()
    result = subprocess.run(
        ["bash", str(REPO_ROOT / "install-skill.sh"), str(target)],
        capture_output=True, text=True,
        env={**os.environ, "SLOPSTOPPER_REPO_RAW": f"file://{REPO_ROOT}"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for skill in ("slopstopper-install", "slopstopper-triage"):
        text = (target / ".claude/skills" / skill / "SKILL.md").read_text()
        refs = set(re.findall(r"references/([A-Za-z0-9_.-]+\.md)", text))
        assert refs, skill
        for ref in refs:
            assert (target / ".claude/skills" / skill / "references" / ref).is_file(), f"{skill}/{ref}"


def test_install_skill_sh_ships_only_the_files_the_map_links(tmp_path):
    src = _skill_source(tmp_path)
    (src / ".claude/skills/slopstopper-install/references/wip.md").write_text("# draft\n")
    (src / ".claude/skills/slopstopper-install/.DS_Store").write_text("junk")
    target = tmp_path / "adopter"
    target.mkdir()
    result = _run_install_skill(target, src)
    assert result.returncode == 0, result.stdout + result.stderr
    installed = target / ".claude/skills/slopstopper-install"
    assert not (installed / "references/wip.md").exists()
    assert not (installed / ".DS_Store").exists()


def test_a_failed_skill_leaves_the_installed_copy_and_fails_loudly(tmp_path):
    src = _skill_source(tmp_path)
    target = tmp_path / "adopter"
    target.mkdir()
    assert _run_install_skill(target, src).returncode == 0
    installed = target / ".claude/skills/slopstopper-install"
    before = (installed / "SKILL.md").read_text()
    skill_src = src / ".claude/skills/slopstopper-install"
    (skill_src / "SKILL.md").write_text(before + "\nnew upstream line\n")
    (skill_src / "references/verify.md").unlink()
    triage_md = src / ".claude/skills/slopstopper-triage/SKILL.md"
    triage_md.write_text(triage_md.read_text() + "\ntriage update\n")
    result = _run_install_skill(target, src)
    assert result.returncode == 1
    assert "slopstopper-install" in result.stdout + result.stderr
    assert (installed / "SKILL.md").read_text() == before
    assert (installed / "references/verify.md").is_file()
    assert "triage update" in (target / ".claude/skills/slopstopper-triage/SKILL.md").read_text()
    leftovers = [p.name for p in (target / ".claude/skills").iterdir() if "." in p.name]
    assert not leftovers, leftovers


def test_installed_skill_directories_follow_the_umask(tmp_path):
    src = _skill_source(tmp_path)
    target = tmp_path / "adopter"
    target.mkdir()
    assert _run_install_skill(target, src, umask="022").returncode == 0
    for path in (
        target / ".claude/skills/slopstopper-install",
        target / ".claude/skills/slopstopper-install/references",
    ):
        assert stat.S_IMODE(path.stat().st_mode) == 0o755, path


# ── the config seed is a starter, not the schema ─────────────────

STARTER = REPO_ROOT / "templates" / "slopstopper.yml.starter"
EXAMPLE = REPO_ROOT / ".slopstopper.yml.example"


def _leaves(tree: dict, prefix: str = "") -> dict:
    out: dict = {}
    for k, v in tree.items():
        if isinstance(v, dict) and v:
            out |= _leaves(v, f"{prefix}{k}.")
        else:
            out[f"{prefix}{k}"] = v
    return out


def _keys(tree: dict) -> set[str]:
    paths = set(_leaves(tree))
    return paths | {p.rsplit(".", n)[0] for p in paths for n in range(1, p.count(".") + 1)}


def test_the_starter_is_short_and_parses():
    from slopstopper import config

    assert STARTER.is_file()
    assert len(STARTER.read_text().splitlines()) <= 60, "the starter should stay under a screenful"
    tree = config._load_yaml_subset(STARTER)
    assert tree["profile"] == "ui"
    assert "urls" in tree and "pages" in tree and "workflows" in tree


def test_every_starter_key_exists_in_the_schema_reference():
    from slopstopper import config

    starter_keys = _keys(config._load_yaml_subset(STARTER))
    example_keys = _keys(config._load_yaml_subset(EXAMPLE))
    assert starter_keys <= example_keys, sorted(starter_keys - example_keys)


def test_the_starter_seeds_the_schemas_defaults():
    from slopstopper import config

    starter = _leaves(config._load_yaml_subset(STARTER))
    example = _leaves(config._load_yaml_subset(EXAMPLE))
    drifted = {k: (v, example[k]) for k, v in starter.items() if k in example and example[k] != v}
    assert not drifted, drifted


def test_the_starter_describes_the_ui_api_holdback():
    starter = STARTER.read_text()
    assert "ship inert" not in starter
    assert "re-run" in starter and "format: meta" in starter

