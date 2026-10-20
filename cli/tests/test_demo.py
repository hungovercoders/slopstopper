"""`slopstopper demo` writes the fixture repo, and the fixture fails the
two checks it promises to fail, each with exactly its one finding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopstopper import cli, config, demo
from slopstopper.checks import docs_structure, entry_files


def test_the_fixture_has_the_agents_first_layout():
    names = [published for published, _ in demo.files()]
    for expected in (
        "README.md", "AGENTS.md", "CLAUDE.md", "docs/README.md",
        "docs/runbooks/RELEASE.md", ".slopstopper.yml", ".gitignore", "app/index.html",
    ):
        assert expected in names
    assert not any(Path(n).name in demo.RENAMES for n in names), "stored names are published renamed"


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


def test_cli_writes_and_names_the_two_failures(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["demo"]) == 0
    out = capsys.readouterr().out
    assert (tmp_path / demo.DEFAULT_OUT / "AGENTS.md").exists()
    assert "hygiene:entry-files" in out and "hygiene:docs-structure" in out
    assert f"cd {demo.DEFAULT_OUT} && slopstopper run hygiene:entry-files" in out


def test_cli_json_shape(tmp_path, capsys):
    out_dir = tmp_path / "lantern"
    assert cli.main(["demo", "--out", str(out_dir), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data) == {"out", "written", "skipped", "failures"}
    assert data["out"] == str(out_dir)
    assert str(out_dir / ".slopstopper.yml") in data["written"]
    assert data["skipped"] == []
    assert [f["check"] for f in data["failures"]] == ["hygiene:entry-files", "hygiene:docs-structure"]
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


def test_renames_apply_at_the_root_only_and_junk_is_skipped(monkeypatch, tmp_path):
    fake = tmp_path / "demo"
    (fake / "docs").mkdir(parents=True)
    (fake / "__pycache__").mkdir()
    (fake / "slopstopper.yml").write_text("profile: ui\n")
    (fake / "docs" / "slopstopper.yml").write_text("sample\n")
    (fake / "docs" / "notes.md~").write_text("backup\n")
    (fake / "__pycache__" / "x.pyc").write_bytes(b"")
    (fake / ".DS_Store").write_bytes(b"")
    monkeypatch.setattr(demo, "DEMO_DIR", fake)
    assert sorted(n for n, _ in demo.files()) == [".slopstopper.yml", "docs/slopstopper.yml"]


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
