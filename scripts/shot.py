#!/usr/bin/env python3
"""Render the site's terminal demo as an animated SVG from real CLI output.

    task contributing:shots            # writes app/assets/demo.svg
    python scripts/shot.py --out DIR   # somewhere else (CI uploads it)

No VHS, ttyd or ffmpeg: the script runs the commands below with the
interpreter it was started from, captures what they print, and draws
each line into a terminal window as SVG text. An animation shows the
screens one after another and loops; `prefers-reduced-motion` gets the
last screen, still. The result is a few kilobytes, same-origin (so the
site's CSP needs nothing), and diffable in a PR.

Run it from the repository root: the hygiene check reads this repo's
entry files, so the picture shows slopstopper checking slopstopper.
Re-run after changing what a command prints (see CHANGE_MAP).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from xml.sax.saxutils import escape

# ── what the picture shows ───────────────────────────────────────

# (what the prompt shows, the argv that produces it). The CLI runs as a
# module of the interpreter running this script, so the editable install
# in cli/.venv is what gets recorded, never a wheel earlier on PATH.
CLI = [sys.executable, "-m", "slopstopper"]
SCREENS: list[tuple[str, list[str]]] = [
    ("slopstopper checks list", [*CLI, "checks", "list"]),
    ("slopstopper run hygiene:entry-files", [*CLI, "run", "hygiene:entry-files"]),
]

# ── geometry, in SVG user units ──────────────────────────────────

FONT_SIZE = 13.0
CELL_W = FONT_SIZE * 0.6      # the advance of a monospace glyph at this size
LINE_H = 18.0
PAD_X = 18.0
BAR_H = 36.0
FIRST_BASELINE = BAR_H + 24.0
BOTTOM = 22.0
COLS = 112                    # the terminal's width; longer lines wrap

# Timing, in seconds. Each screen types its command, shows its output,
# holds, then the next screen takes over; the whole thing loops.
TYPE_PER_CHAR = 0.045
LINE_STAGGER = 0.03
HOLD = 5.0
GAP = 0.6

# The site's brand tokens (app/shared.css), as the .codeblock uses them.
INK = "#2A2118"
CREAM = "#FBF5EC"
SUN = "#F5C24C"
INK_SOFT = "#6B5B47"
BAR = "#3A2E22"


def capture(argv: list[str], cwd: Path) -> str:
    """What the command prints, with colour off so the text is plain."""
    env = {**os.environ, "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        argv, cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )
    return result.stdout


def cells(text: str) -> int:
    """Terminal columns the text takes: emoji and East Asian wide glyphs
    are two cells; combining marks and variation selectors are none."""
    width = 0
    for char in text:
        if unicodedata.combining(char) or char in "︎️‍":
            continue
        if unicodedata.east_asian_width(char) in ("W", "F") or ord(char) >= 0x1F000:
            width += 2
        else:
            width += 1
    return width


def wrap(line: str, cols: int = COLS) -> list[str]:
    """Break a line the way the terminal would, at the column limit."""
    out, current, width = [], "", 0
    for char in line:
        w = cells(char)
        if width + w > cols and current:
            out.append(current)
            current, width = "", 0
        current += char
        width += w
    out.append(current)
    return out


def screen_lines(command: str, output: str) -> list[tuple[str, str]]:
    """(kind, text) rows: the prompt line, then the output, wrapped."""
    rows: list[tuple[str, str]] = [("prompt", command)]
    for line in output.rstrip("\n").splitlines():
        for part in wrap(line.rstrip()):
            rows.append(("out", part))
    rows.append(("cursor", ""))
    return rows


def text_el(row: int, text: str, fill: str, x: float = PAD_X, extra: str = "") -> str:
    y = FIRST_BASELINE + row * LINE_H
    width = cells(text) * CELL_W
    attrs = f'x="{x:.1f}" y="{y:.1f}" fill="{fill}"{extra}'
    if width:
        # Hold the grid whatever monospace face the reader has.
        attrs += f' textLength="{width:.1f}" lengthAdjust="spacingAndGlyphs"'
    return f'<text {attrs} xml:space="preserve">{escape(text)}</text>'


def _timeline(screens: list[tuple[str, list[tuple[str, str]]]]) -> tuple[list[tuple[float, float, float]], float]:
    """Each screen's slot on the loop (start, typing time, end) and the
    loop's length: type the command, reveal the output a line at a time,
    hold, then hand over."""
    slots, t = [], 0.0
    for command, rows in screens:
        typing = len(command) * TYPE_PER_CHAR
        reveal = (len(rows) - 1) * LINE_STAGGER
        slots.append((t, typing, t + typing + reveal + HOLD))
        t = slots[-1][2] + GAP
    return slots, t


class _Clock:
    """Turns seconds on the loop into keyframe percentages and emits the
    show/hide rules each element needs."""

    def __init__(self, total: float) -> None:
        self.total = total
        self.css: list[str] = []

    def pct(self, seconds: float) -> str:
        return f"{100.0 * seconds / self.total:.3f}%"

    def visible(self, key: str, show: float, hide: float | None) -> None:
        """`key` appears at `show` and, if `hide` is given, goes at `hide`."""
        frames = f"0%,{self.pct(show)}{{opacity:0}}{self.pct(show + 0.001)}"
        if hide is None:
            frames += ",100%{opacity:1}"
        else:
            frames += f",{self.pct(hide)}{{opacity:1}}{self.pct(hide + 0.001)},100%{{opacity:0}}"
        self.css.append(f"@keyframes {key}{{{frames}}}")
        self.css.append(f".{key}{{animation:{key} {self.total:.2f}s linear infinite}}")


def _prompt_row(clock: _Clock, name: str, row: int, text: str, start: float) -> list[str]:
    """The command as if typed: one element per prefix, each shown for a
    keystroke; the full command is a row (it stays), the prefixes are the
    typing and vanish without motion."""
    parts = [text_el(row, "$ ", SUN)]
    chars = len(text)
    for n in range(1, chars + 1):
        key = f"{name}p{n}"
        hide = start + (n + 1) * TYPE_PER_CHAR if n < chars else None
        clock.visible(key, start + n * TYPE_PER_CHAR, hide)
        kind_class = "row" if n == chars else "typed"
        parts.append(text_el(row, text[:n], CREAM, x=PAD_X + 2 * CELL_W, extra=f' class="{kind_class} {key}"'))
    return parts


def _cursor_row(row: int, key: str) -> list[str]:
    y = FIRST_BASELINE + row * LINE_H
    return [
        text_el(row, "$ ", SUN, extra=f' class="row {key}"'),
        f'<rect class="cursor row {key}" x="{PAD_X + 2 * CELL_W:.1f}" y="{y - FONT_SIZE:.1f}" '
        f'width="{CELL_W:.1f}" height="{FONT_SIZE + 3:.1f}"/>',
    ]


def _screen(clock: _Clock, index: int, rows: list[tuple[str, str]], slot: tuple[float, float, float]) -> str:
    """One screen's group: visible for its slot, its rows revealed in turn."""
    start, typing, end = slot
    name = f"s{index}"
    # The first screen is up from the start, so the loop opens on a prompt.
    if index == 0:
        clock.css.append(f"@keyframes {name}{{0%,{clock.pct(end)}{{opacity:1}}{clock.pct(end + 0.001)},100%{{opacity:0}}}}")
        clock.css.append(f".{name}{{animation:{name} {clock.total:.2f}s linear infinite}}")
    else:
        clock.visible(name, start, end)
    parts = [f'<g class="screen {name}">']
    for row, (kind, text) in enumerate(rows):
        if kind == "prompt":
            parts.extend(_prompt_row(clock, name, row, text, start))
            continue
        key = f"{name}r{row}"
        clock.visible(key, start + typing + (row - 1) * LINE_STAGGER, None)
        if kind == "cursor":
            parts.extend(_cursor_row(row, key))
        else:
            parts.append(text_el(row, text, CREAM, extra=f' class="row {key}"'))
    parts.append("</g>")
    return "\n".join(parts)


def _title_bar(width: float, title: str) -> str:
    return (
        f'<rect width="{width:.0f}" height="{BAR_H:.0f}" fill="{BAR}"/>'
        f'<circle cx="20" cy="{BAR_H / 2:.0f}" r="6" fill="#E8512B"/>'
        f'<circle cx="40" cy="{BAR_H / 2:.0f}" r="6" fill="{SUN}"/>'
        f'<circle cx="60" cy="{BAR_H / 2:.0f}" r="6" fill="#2E8B6F"/>'
        f'<text x="{width / 2:.0f}" y="{BAR_H / 2 + 4.5:.1f}" fill="{CREAM}" text-anchor="middle" '
        f'style="font-family:Nunito,ui-rounded,system-ui,sans-serif;font-size:12px;font-weight:700">{escape(title)}</text>'
    )


def render(screens: list[tuple[str, list[tuple[str, str]]]], title: str, still: int | None = None) -> str:
    rows_max = max(len(rows) for _, rows in screens)
    width = PAD_X * 2 + COLS * CELL_W
    height = FIRST_BASELINE + (rows_max - 1) * LINE_H + BOTTOM
    slots, total = _timeline(screens)

    clock = _Clock(total)
    clock.css += [
        f"text{{font-family:ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace;font-size:{FONT_SIZE}px;white-space:pre}}",
        ".screen{opacity:0}",
        ".row{opacity:0}",
        ".typed{opacity:0}",
        f".cursor{{fill:{SUN}}}",
    ]
    body = [_screen(clock, index, rows, slot) for index, ((_, rows), slot) in enumerate(zip(screens, slots))]

    # Reduced motion: no animation, the last screen in full.
    last = f"s{len(screens) - 1}"
    css = clock.css
    css.append(
        "@media (prefers-reduced-motion:reduce){.screen,.row,.typed{animation:none!important;opacity:0}"
        f".{last},.{last} .row{{opacity:1}}}}"
    )
    if still is not None:
        # One screen, no motion: what a reader sees with reduced motion,
        # for checking the picture and for the test.
        css = [rule for rule in css if not rule.startswith("@keyframes") and "animation:" not in rule]
        css.append(f".screen,.row,.typed{{opacity:0}}.s{still},.s{still} .row{{opacity:1}}")

    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-labelledby="t">',
        f"<title id=\"t\">{escape(title)}</title>",
        "<style>" + "".join(css) + "</style>",
        f'<rect width="{width:.0f}" height="{height:.0f}" rx="12" fill="{INK}"/>',
        _title_bar(width, title),
        *body,
        "</svg>",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="app/assets", help="directory to write demo.svg into")
    parser.add_argument(
        "--still", type=int, metavar="N",
        help="write screen N without animation (demo-still-N.svg), for checking the picture",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    screens = []
    for command, argv in SCREENS:
        output = capture(argv, root)
        if not output.strip():
            print(f"shot: {command!r} printed nothing", file=sys.stderr)
            return 1
        screens.append((command, screen_lines(command, output)))
    svg = render(screens, "slopstopper, on its own repository", still=args.still)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / ("demo.svg" if args.still is None else f"demo-still-{args.still}.svg")
    path.write_text(svg, encoding="utf-8")
    print(f"wrote {path} ({len(svg.encode()) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
