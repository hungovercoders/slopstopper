"""The suite `slopstopper install` writes ships inside the package.

`slopstopper.suite` names the files once; the build hook copies them into
the sdist and the wheel, and an editable install reads the checkout. These
tests hold the three in step.
"""

from __future__ import annotations

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from slopstopper import suite

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_ROOT = REPO_ROOT / "cli"


def test_the_checkout_serves_the_suite_to_an_editable_install():
    assert suite.source_root() == REPO_ROOT


def test_every_shipped_path_exists_in_the_checkout():
    missing = [rel for rel in suite.shipped_paths(REPO_ROOT) if not (REPO_ROOT / rel).is_file()]
    assert not missing, missing


def test_the_shipped_set_is_the_whole_installer_surface():
    paths = set(suite.shipped_paths(REPO_ROOT))
    assert "Taskfile.ss.yml" in paths and "package.json" in paths and ".githooks/pre-push" in paths
    assert {p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / "templates").iterdir()} <= paths
    assert {f".github/workflows/{name}" for name in suite.GENERIC_WORKFLOWS} <= paths
    for action in (REPO_ROOT / ".github/actions").glob("ss-*"):
        assert f"{action.relative_to(REPO_ROOT).as_posix()}/action.yml" in paths
    for skill in suite.SKILLS:
        assert f".claude/skills/{skill}/SKILL.md" in paths
    assert not [p for p in paths if p.startswith(".github/workflows/ci-")], "this repo's own CI never ships"


def test_a_skill_ships_only_the_references_its_map_links(tmp_path):
    src = tmp_path / "src"
    skill = src / ".claude/skills/slopstopper-install"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: x\n---\nSee references/install.md and references/verify.md.\n")
    for name in ("install.md", "verify.md", "wip.md"):
        (skill / "references" / name).write_text("# draft\n")
    assert suite.skill_files(src, "slopstopper-install") == [
        ".claude/skills/slopstopper-install/SKILL.md",
        ".claude/skills/slopstopper-install/references/install.md",
        ".claude/skills/slopstopper-install/references/verify.md",
    ]


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> dict[str, Path]:
    """The sdist, and the wheel built from it, as `python -m build` does."""
    out = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out), str(CLI_ROOT)],
        capture_output=True, text=True, cwd=CLI_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return {"sdist": next(out.glob("*.tar.gz")), "wheel": next(out.glob("*.whl"))}


def test_the_sdist_carries_the_suite(built):
    with tarfile.open(built["sdist"]) as tar:
        names = {n.split("/", 1)[1] for n in tar.getnames() if "/" in n}
    expected = {f"suite/{rel}" for rel in suite.shipped_paths(REPO_ROOT)}
    assert expected <= names, sorted(expected - names)


def test_the_wheel_carries_the_suite_where_the_cli_looks(built):
    with zipfile.ZipFile(built["wheel"]) as whl:
        names = set(whl.namelist())
        shipped = whl.read("slopstopper/data/suite/Taskfile.ss.yml")
    expected = {f"slopstopper/data/suite/{rel}" for rel in suite.shipped_paths(REPO_ROOT)}
    assert expected <= names, sorted(expected - names)
    assert shipped == (REPO_ROOT / "Taskfile.ss.yml").read_bytes()
    assert not [n for n in names if "/suite/.github/workflows/ci-" in n]
