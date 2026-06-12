"""Shared pytest fixtures for the slopstopper-cli test suite."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

from slopstopper import config


@pytest.fixture
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """chdir into a tmp_path and reset the config cache around the test.

    The config module reads `.slopstopper.yml` from CWD and caches the
    result at module level. Tests that lay out a fake repo or edit
    `.slopstopper.yml` need a clean slate both before and after.
    """
    monkeypatch.chdir(tmp_path)
    config.reload()
    yield tmp_path
    config.reload()


@pytest.fixture
def write_config(isolated_cwd: Path) -> callable:
    """Write a `.slopstopper.yml` into the isolated CWD and clear the config cache."""

    def _write(body: str) -> Path:
        path = isolated_cwd / ".slopstopper.yml"
        path.write_text(body)
        config.reload()
        return path

    return _write


@pytest.fixture
def docs_tree(isolated_cwd: Path) -> callable:
    """Build a `docs/` tree under the isolated CWD from a {relpath: content} mapping."""

    def _build(files: dict[str, str | bytes]) -> Path:
        docs = isolated_cwd / "docs"
        docs.mkdir(exist_ok=True)
        for relpath, content in files.items():
            target = docs / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content)
        return docs

    return _build
