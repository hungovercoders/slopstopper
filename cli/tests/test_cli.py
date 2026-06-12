"""Tests for the CLI dispatcher (cli.py)."""

from __future__ import annotations

import pytest

from slopstopper import cli


def test_version_flag_prints_and_exits(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "slopstopper" in out


def test_run_unknown_check_returns_2(capsys):
    rc = cli.main(["run", "no-such:check"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown check" in err
    assert "known checks" in err


def test_no_command_errors(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code != 0
