"""Tests for the security:licences check."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopstopper.checks import licences


POLICY = """# the allowlist
allow-licenses:
  - MIT
  - Apache-2.0
  - BSD-3-Clause
  - ISC   # trailing comment
  - 'MPL-2.0'

allow-dependencies-licenses:
  - pkg:npm/%40img/sharp-libvips-linux-x64
  - pkg:pypi/Some_Package
"""


def _lock(packages: dict) -> str:
    return json.dumps({"name": "site", "lockfileVersion": 3, "packages": {"": {"name": "site", "version": "1.0.0"}, **packages}})


def _pkg(version="1.0.0", licence="MIT", dev=False, **extra):
    entry = {"version": version, "license": licence}
    if dev:
        entry["dev"] = True
    entry.update(extra)
    return entry


@pytest.fixture
def repo(isolated_cwd: Path):
    (isolated_cwd / ".github").mkdir()
    (isolated_cwd / ".github/dependency-review-config.yml").write_text(POLICY)
    return isolated_cwd


def _report() -> dict:
    return json.loads(Path(".ss/reports/licences/licences-report.json").read_text())


# ── the policy ───────────────────────────────────────────────────


def test_policy_lists_are_read_with_comments_and_quotes_stripped(repo):
    policy = licences._read_policy(repo / ".github/dependency-review-config.yml")
    assert policy["allow"] == {"mit", "apache-2.0", "bsd-3-clause", "isc", "mpl-2.0"}
    assert policy["deny"] == set()
    assert policy["exempt"] == {"npm:@img/sharp-libvips-linux-x64", "pypi:some-package"}


@pytest.mark.parametrize("expression, expected", [
    ("MIT", True),
    ("mit", True),
    ("GPL-3.0-only", False),
    ("(MIT OR GPL-3.0-only)", True),
    ("MIT AND GPL-3.0-only", False),
    ("(Apache-2.0 AND MIT) OR GPL-2.0-only", True),
    ("GPL-2.0-only WITH Classpath-exception-2.0", False),
    ("MIT WITH LLVM-exception", True),
    ("Apache License 2.0", True),
    ("Apache License, Version 2.0", True),
    ("3-Clause BSD License", True),
    ("MIT license", True),
    ("BSD", None),
    ("Dual License", None),
    ("SEE LICENSE IN LICENSE", None),
    ("(MIT OR", None),
    ("", None),
])
def test_spdx_expressions_against_the_allowlist(repo, expression, expected):
    policy = licences._read_policy(repo / ".github/dependency-review-config.yml")
    assert licences._allowed(expression, policy) is expected


def test_a_deny_list_inverts_the_rule(repo):
    (repo / ".github/dependency-review-config.yml").write_text("deny-licenses:\n  - GPL-3.0-only\n")
    policy = licences._read_policy(repo / ".github/dependency-review-config.yml")
    assert licences._allowed("MIT", policy) is True
    assert licences._allowed("GPL-3.0-only", policy) is False
    assert licences._allowed("Made-Up-1.0", policy) is None


# ── npm ──────────────────────────────────────────────────────────


def test_a_clean_lockfile_passes_and_dev_dependencies_are_not_judged(repo, capsys):
    (repo / "package-lock.json").write_text(_lock({
        "node_modules/a": _pkg(licence="MIT"),
        "node_modules/a/node_modules/b": _pkg(licence="(MIT OR Apache-2.0)"),
        "node_modules/gpl-tool": _pkg(licence="GPL-3.0-only", dev=True),
    }))
    assert licences.run() == 0
    out = capsys.readouterr().out
    assert "1 devDependencies not judged" in out
    assert _report()["judged"] == 2


def test_include_dev_judges_dev_dependencies_too(repo, write_config):
    (repo / "package-lock.json").write_text(_lock({"node_modules/gpl-tool": _pkg(licence="GPL-3.0-only", dev=True)}))
    write_config("security:\n  licences:\n    include_dev: true\n")
    assert licences.run() == 1
    assert [p["name"] for p in _report()["denied"]] == ["gpl-tool"]


def test_a_denied_transitive_licence_fails_and_is_named(repo, capsys):
    (repo / "package-lock.json").write_text(_lock({
        "node_modules/a": _pkg(),
        "node_modules/a/node_modules/deep": _pkg(version="2.1.0", licence="AGPL-3.0-only"),
    }))
    assert licences.run() == 1
    assert "deep (AGPL-3.0-only)" in capsys.readouterr().out
    report = Path(".ss/reports/licences/licences-report.md").read_text()
    assert "| `deep` | 2.1.0 | npm | AGPL-3.0-only |" in report
    assert "allow-dependencies-licenses" in report


def test_an_exempt_package_passes_whatever_its_licence(repo):
    (repo / "package-lock.json").write_text(_lock({"node_modules/@img/sharp-libvips-linux-x64": _pkg(licence="LGPL-3.0-or-later")}))
    assert licences.run() == 0
    assert _report()["denied"] == []


def test_unknown_and_missing_licences_are_reported_not_failed(repo, capsys):
    (repo / "package-lock.json").write_text(_lock({
        "node_modules/legacy": {"version": "0.1.0", "licenses": [{"type": "MIT"}, {"type": "GPL-2.0-only"}]},
        "node_modules/odd": _pkg(licence="SEE LICENSE IN LICENSE"),
        "node_modules/none": {"version": "0.0.1"},
    }))
    assert licences.run() == 0
    assert "2 package(s) state no SPDX licence" in capsys.readouterr().out
    assert sorted(p["name"] for p in _report()["unknown"]) == ["none", "odd"]


def test_a_version_one_lockfile_cannot_run(repo, capsys):
    (repo / "package-lock.json").write_text(json.dumps({"lockfileVersion": 1, "dependencies": {"a": {"version": "1.0.0"}}}))
    assert licences.run() == 2
    assert "lockfile version 1" in capsys.readouterr().out


def test_a_lockfile_one_directory_down_counts_and_yarn_is_noted(repo, capsys):
    (repo / "site").mkdir()
    (repo / "site/package-lock.json").write_text(_lock({"node_modules/a": _pkg(licence="GPL-3.0-only")}))
    (repo / "yarn.lock").write_text("")
    assert licences.run() == 1
    assert "`yarn.lock` carries no licence data" in capsys.readouterr().out


# ── Python ───────────────────────────────────────────────────────


def _fake_pip(monkeypatch, metadata: list[dict], *, rc: int = 0):
    def fake_run(cmd, **_kwargs):
        class P:
            returncode = rc
            stdout = json.dumps({"installed": [{"metadata": m} for m in metadata]})
            stderr = "" if rc == 0 else "ERROR: unknown command inspect"
        return P()
    monkeypatch.setattr(licences.subprocess, "run", fake_run)
    monkeypatch.setattr(licences.shutil, "which", lambda name: f"/usr/bin/{name}")


def test_python_packages_are_judged_from_pip_inspect(repo, monkeypatch, capsys):
    (repo / "pyproject.toml").write_text('[project]\nname = "my-tool"\nlicense = {text = "GPL-3.0-only"}\ndependencies = ["requests>=2", "Some_Package"]\n')
    _fake_pip(monkeypatch, [
        {"name": "my-tool", "version": "0.1", "license": "GPL-3.0-only"},
        {"name": "requests", "version": "2.32.0", "license": "Apache-2.0"},
        {"name": "some-package", "version": "1.0", "license": "AGPL-3.0-only"},
        {"name": "classified", "version": "1.0", "license": "", "classifier": ["License :: OSI Approved :: MIT License"]},
        {"name": "modern", "version": "1.0", "license_expression": "MIT OR Apache-2.0"},
        {"name": "copyleft", "version": "1.0", "license": "GNU General Public License v3 (GPLv3)", "classifier": ["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"]},
    ])
    assert licences.run() == 1
    report = _report()
    assert report["per_ecosystem"] == {"pypi": 5}, "the project itself is not judged"
    assert [p["name"] for p in report["denied"]] == ["copyleft"]
    assert "copyleft (GPL-3.0-only)" in capsys.readouterr().out


def test_an_environment_without_the_declared_dependencies_cannot_run(repo, monkeypatch, capsys):
    (repo / "requirements.txt").write_text("# deps\nrequests>=2\n-r other.txt\n")
    _fake_pip(monkeypatch, [{"name": "pip", "version": "24.0", "license": "MIT"}])
    assert licences.run() == 2
    assert "none of the dependencies declared in `requirements.txt` is installed" in capsys.readouterr().out


def test_an_old_pip_without_inspect_cannot_run(repo, monkeypatch, capsys):
    (repo / "requirements.txt").write_text("requests\n")
    _fake_pip(monkeypatch, [], rc=2)
    assert licences.run() == 2
    assert "pip 22.2 or newer" in capsys.readouterr().out


def test_a_venv_beside_the_manifest_is_inspected_first(repo, monkeypatch):
    (repo / "cli").mkdir()
    (repo / "cli/pyproject.toml").write_text('[project]\nname = "x"\ndependencies = ["lizard"]\n')
    (repo / "cli/.venv/bin").mkdir(parents=True)
    (repo / "cli/.venv/bin/python").write_text("")
    assert licences._python_interpreter(repo, [repo / "cli/pyproject.toml"]) == str(repo / "cli/.venv/bin/python")
    monkeypatch.setattr(licences.shutil, "which", lambda name: "/usr/bin/python3")
    (repo / "cli/.venv/bin/python").unlink()
    assert licences._python_interpreter(repo, [repo / "cli/pyproject.toml"]) == "/usr/bin/python3"


# ── the contract ─────────────────────────────────────────────────


def test_no_policy_file_cannot_run(isolated_cwd, capsys):
    (isolated_cwd / "package-lock.json").write_text(_lock({}))
    assert licences.run() == 2
    assert "No licence policy" in capsys.readouterr().out


def test_nothing_to_inventory_passes(repo, capsys):
    assert licences.run() == 0
    assert "nothing to inventory" in capsys.readouterr().out


def test_arguments_are_rejected(repo):
    assert licences.run(["--foo"]) == 2
