"""Shared output formatters for the slopstopper CLI.

Every check's `run()` calls into these helpers instead of bare `print()`
so the user sees one consistent visual language across the suite:

  ┌─ running()      🔍 What's about to run
  ├─ section()      ━━━ A section break with a title
  ├─ status()       ✅ / ❌ / ⚠️ status lines per finding
  ├─ footer()       📁 Where the reports landed
  └─ separator()    ━━━ A bare horizontal rule

The `--quiet` global flag (top-level in `cli.py`) sets `QUIET = True`
here so the formatters become no-ops; checks still write reports to
disk, but CI logs stay clean.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

# Toggled by `cli.main()` when `--quiet` is passed. Module-global so
# `cli.py` can flip it once and every check picks it up via the
# formatters below — no need to thread a parameter through every
# subprocess wrapper.
QUIET = False

# Width of the horizontal-rule separator. 60 chars fits an 80-col
# terminal with room for prefix indentation. Stay in lockstep across
# checks so section breaks look uniform.
SEPARATOR_WIDTH = 60


def set_quiet(quiet: bool) -> None:
    """Toggle decorative output suppression for the current process."""
    global QUIET
    QUIET = quiet


def _emit(line: str = "", *, force: bool = False, stream=None) -> None:
    """Write a single line to stdout (or the override stream).

    `force=True` bypasses the quiet flag — use for genuine errors that
    should land even with `--quiet`.
    """
    if QUIET and not force:
        return
    target = stream if stream is not None else sys.stdout
    print(line, file=target)


def running(message: str) -> None:
    """Mark the start of a check or major step. `🔍 <message>`."""
    _emit(f"🔍 {message}")


def section(title: str, emoji: str = "") -> None:
    """Print a titled section break: separator, title, separator."""
    if QUIET:
        return
    _emit(separator_str())
    prefix = f"{emoji} " if emoji else ""
    _emit(f"{prefix}{title}")
    _emit(separator_str())


def status(emoji: str, message: str, *, force: bool = False) -> None:
    """Print a status line — pass/fail/warn/info. `<emoji> <message>`.

    `force=True` keeps the line under `--quiet` (use for terminal errors).
    """
    _emit(f"{emoji} {message}", force=force)


def info(message: str) -> None:
    """Neutral informational line. `ℹ️ <message>`."""
    _emit(f"ℹ️  {message}")


def success(message: str) -> None:
    """Pass / green-path status. `✅ <message>`."""
    _emit(f"✅ {message}")


def warn(message: str) -> None:
    """Warning that doesn't fail the check. `⚠️ <message>`."""
    _emit(f"⚠️  {message}")


def error(message: str) -> None:
    """Hard failure — always emitted (even with `--quiet`).

    Stays on stdout (not stderr) to preserve compatibility with existing
    checks and tests that asserted on `capsys.readouterr().out`. The
    `force=True` keeps the line visible under `--quiet`.
    """
    _emit(f"❌ {message}", force=True)


def separator(width: int = SEPARATOR_WIDTH) -> None:
    """Emit a horizontal rule."""
    _emit(separator_str(width))


def separator_str(width: int = SEPARATOR_WIDTH) -> str:
    """Build the separator string without printing it (for embedding)."""
    return "━" * width


def footer(report_dir: Path, files: Iterable[str] = ()) -> None:
    """Standard footer naming the report dir + the files dropped in it.

    Always appears after a check completes so the user knows where to
    look. Honours `--quiet`.
    """
    if QUIET:
        return
    _emit()
    _emit(f"📁 Reports saved to: {report_dir}/")
    for f in files:
        _emit(f"   • {f}")


def blank() -> None:
    """Emit a blank line (honours `--quiet`)."""
    _emit()
