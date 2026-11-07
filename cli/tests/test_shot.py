"""scripts/shot.py draws the site's terminal demo from real CLI output.

It is a script rather than a package module, so it is loaded by path.
These tests pin the pieces a wrong change would silently break: the
column arithmetic that keeps emoji lines aligned, the wrap at the
terminal's width, XML escaping, and that the whole thing runs against
this repository and yields a well-formed SVG with both screens in it.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import xml.dom.minidom
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "shot.py"


@pytest.fixture(scope="module")
def shot():
    spec = importlib.util.spec_from_file_location("shot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cells_counts_emoji_as_two_columns(shot):
    assert shot.cells("abc") == 3
    assert shot.cells("✅ ok") == 5
    assert shot.cells("💤 x") == 4
    # A variation selector adds no column of its own.
    assert shot.cells("⚠️") == shot.cells("⚠")


def test_wrap_breaks_at_the_terminal_width(shot):
    line = "x" * (shot.COLS + 5)
    parts = shot.wrap(line)
    assert [len(p) for p in parts] == [shot.COLS, 5]
    assert shot.wrap("short") == ["short"]


def test_screen_lines_start_with_the_prompt_and_end_with_a_cursor(shot):
    rows = shot.screen_lines("slopstopper x", "one\ntwo\n")
    assert rows[0] == ("prompt", "slopstopper x")
    assert rows[1:3] == [("out", "one"), ("out", "two")]
    assert rows[-1] == ("cursor", "")


def test_render_escapes_markup_and_holds_the_grid(shot):
    rows = shot.screen_lines("cmd", "a <b> & c\n")
    svg = shot.render([("cmd", rows)], "t")
    assert "&lt;b&gt; &amp; c" in svg
    assert "<b>" not in svg
    assert 'lengthAdjust="spacingAndGlyphs"' in svg
    assert "prefers-reduced-motion" in svg
    xml.dom.minidom.parseString(svg)


def test_the_script_draws_both_screens_from_this_repo(shot, tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(tmp_path)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    svg = (tmp_path / "demo.svg").read_text(encoding="utf-8")
    xml.dom.minidom.parseString(svg)
    assert "slopstopper checks list" in svg
    assert "hygiene:entry-files" in svg
    assert "hygiene:docs-size" in svg  # a line of the first screen's output
    assert 'class="screen s0"' in svg and 'class="screen s1"' in svg
    dark = (tmp_path / "demo-dark.svg").read_text(encoding="utf-8")
    xml.dom.minidom.parseString(dark)
    assert "slopstopper checks list" in dark
    # The same screens, so the same size, in the dark theme's colours only.
    assert _view_box(dark) == _view_box(svg)
    assert shot.DARK.bg in dark and shot.DARK.fg in dark
    assert shot.LIGHT.bg not in dark and shot.LIGHT.fg not in dark


def _view_box(svg: str) -> str:
    return re.search(r'viewBox="([^"]+)"', svg).group(1)


def test_the_palettes_are_the_stylesheets_code_block_colours(shot):
    """shot.py copies --code-bg / --code-fg / --code-accent from app/shared.css;
    a retuned token that is not copied here leaves the hero a different colour
    from every code block around it."""
    css = (REPO_ROOT / "app" / "shared.css").read_text(encoding="utf-8")
    for pal in shot.PALETTES:
        for colour in (pal.bg, pal.fg, pal.accent):
            assert colour in css, f"{pal.name or 'light'} palette colour {colour} is not in app/shared.css"


def test_the_home_page_declares_the_recordings_size():
    """index.html's width/height on both <img> must equal the SVGs' viewBox,
    or the hero reserves the wrong box and shifts when the recording loads."""
    page = (REPO_ROOT / "app" / "index.html").read_text(encoding="utf-8")
    for name in ("demo.svg", "demo-dark.svg"):
        svg = (REPO_ROOT / "app" / "assets" / name).read_text(encoding="utf-8")
        _, _, width, height = _view_box(svg).split()
        tag = re.search(rf'<img[^>]*src="assets/{re.escape(name)}"[^>]*>', page).group(0)
        assert f'width="{width}"' in tag and f'height="{height}"' in tag, f"{name}: index.html declares another size"
