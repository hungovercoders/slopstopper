#!/usr/bin/env python3
"""Write each lesson's VHS tape from its runnable blocks, so the b-roll
of an episode cannot drift from the lesson it belongs to.

Every page under docs/learn/ marks the blocks a reader types (see
scripts/learncheck.py, which runs them). This script turns those blocks,
in order, into `docs/learn/tapes/<NN>.tape`: a VHS script that types each
line into a terminal of the size the episode conventions fix (100
columns by 30 rows at font size 16, the site's theme), clears between
blocks, waits for each block's last command to finish, and holds its
output on screen for a beat. A tape is committed next to
its lesson, and `--check` fails when one is stale, so a lesson edit
without `task contributing:learn:tapes` is caught in CI.

The tapes are recorded by demos/render.sh (`task contributing:learn:record`)
in a scratch clone with the CLI on PATH, the same sandbox the harness
uses, so the terminal in an episode shows what a reader sees.

Usage:
    python scripts/learntapes.py                 # (re)write every tape
    python scripts/learntapes.py --page 08       # the tapes whose lesson starts with 08
    python scripts/learntapes.py --check         # report stale tapes, write nothing

Exit codes follow the suite's contract: 0 every tape is written (or, with
--check, current), 1 a tape is stale, a command in a block cannot be
typed, or a tape has no lesson, 2 there are no lessons to read.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learncheck import Block, extract, pages  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TAPES = ROOT / "docs" / "learn" / "tapes"

# One terminal, 100 columns by 30 rows, font size 16, as docs/learn/EPISODES.md
# fixes it. Measured with vhs 0.10 and its default font: the window gains
# one column per 10 px of width and one row per 20 px of height, and
# these two sizes come out at exactly 100x30 (`echo $COLUMNS $LINES` in a
# test tape is the way to re-measure after a vhs upgrade).
FONT_SIZE = 16
WIDTH = 1070
HEIGHT = 620
PADDING = 20
TYPING = "40ms"
HEREDOC_TYPING = "8ms"
# After a block's last line, the tape waits for the prompt to come back
# (render.sh's prompt is `$ `, which vhs reads back without its trailing
# space; a check can take a minute or two, hence the long timeout) and
# then holds the output on screen for a beat.
WAIT = "Wait+Line@5m /^\\$$/"
PAUSE = "2s"
PAUSE_CHECK = "3s"

_HEADING = re.compile(r"^(#{2,3}) (.+)$", re.M)
_HEREDOC = re.compile(r"<<-?\s*'?\"?(?P<tag>\w+)'?\"?\s*$")


def tape_for(page: Path) -> Path:
    return TAPES / f"{page.name[:2]}.tape"


def heading_before(text: str, line: int) -> str | None:
    """The nearest `##`/`###` heading above the given 1-based line."""
    found = None
    for m in _HEADING.finditer(text):
        if text.count("\n", 0, m.start()) + 1 >= line:
            break
        found = m.group(2).strip()
    return found


def quote(line: str) -> str:
    """A vhs string literal for one typed line. vhs strings carry no
    escapes, so the quote is whichever of its three delimiters the line
    does not use."""
    for q in ('"', "'", "`"):
        if q not in line:
            return f"{q}{line}{q}"
    raise ValueError(f"cannot quote a line that uses \", ' and `: {line!r}")


def untypeable(line: str) -> str | None:
    """Why vhs could not type this line, or None. vhs sends keystrokes, so
    a character outside printable ASCII is dropped on the way."""
    bad = sorted({c for c in line if not 32 <= ord(c) <= 126})
    if bad:
        return "cannot be typed by vhs, it drops " + " ".join(repr(c) for c in bad)
    return None


def shot(block: Block, text: str, heading: str | None, first: bool) -> tuple[list[str], list[str]]:
    """The tape lines for one block, and any lines in it vhs cannot type."""
    out: list[str] = []
    problems: list[str] = []
    if heading:
        out.append(f"# {heading}")
    if not first:
        out.append('Type "clear" Enter')
    terminator: str | None = None
    for raw in block.code.splitlines():
        line = raw.rstrip("\n")
        if (why := untypeable(line)) is not None:
            problems.append(f"{block.where}: {line.strip()[:60]!r} {why}")
            continue
        if not line:
            out.append("Enter")
        elif terminator is not None:
            out.append(f"Type@{HEREDOC_TYPING} {quote(line)} Enter")
        else:
            out.append(f"Type {quote(line)} Enter")
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
        elif (m := _HEREDOC.search(line)) is not None:
            terminator = m.group("tag")
    runs_check = any(
        line.lstrip().startswith(("task ", "slopstopper run ", "slopstopper "))
        for line in block.code.splitlines()
    )
    out.append(WAIT)
    out.append(f"Sleep {PAUSE_CHECK if runs_check else PAUSE}")
    out.append("")
    return out, problems


def render(page: Path) -> tuple[str, list[str]]:
    text = page.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").strip()
    number = page.name[:2]
    lines = [
        f"# {title}.",
        "# The terminal parts of the episode, generated from the lesson's",
        "# runnable blocks by scripts/learntapes.py: edit the lesson, then",
        "# `task contributing:learn:tapes`. Record it with",
        f"# `task contributing:learn:record -- {number}` (demos/render.sh), which",
        "# starts the shell in a scratch clone with the CLI on PATH, fills in",
        f"# the theme from demos/theme.json, and writes dist/learn/{number}.mp4.",
        f"Output demos/.frames/{number}/",
        "Set Shell bash",
        f"Set FontSize {FONT_SIZE}",
        f"Set Width {WIDTH}",
        f"Set Height {HEIGHT}",
        f"Set Padding {PADDING}",
        f"Set TypingSpeed {TYPING}",
        "Set Theme @theme.json",
        "Set Framerate 50",
        "",
    ]
    problems: list[str] = []
    last_heading: str | None = None
    for i, block in enumerate(extract(page)):
        heading = heading_before(text, block.line)
        out, bad = shot(block, text, heading if heading != last_heading else None, first=i == 0)
        last_heading = heading
        lines.extend(out)
        problems.extend(bad)
    return "\n".join(lines).rstrip("\n") + "\n", problems


def validate(tapes: list[Path]) -> int:
    """`vhs validate` on each tape when vhs is on PATH; how many failed.

    A tape carries `Set Theme @theme.json`, which demos/render.sh fills
    in from demos/theme.json at render time, so the copy vhs reads gets
    the same splice."""
    if shutil.which("vhs") is None:
        print("learntapes: vhs is not on PATH, so the tapes' syntax is not validated here")
        return 0
    theme = " ".join((ROOT / "demos" / "theme.json").read_text(encoding="utf-8").split())
    failed = 0
    with tempfile.TemporaryDirectory(prefix="learntapes-") as tmp:
        for tape in tapes:
            copy = Path(tmp) / tape.name
            copy.write_text(
                tape.read_text(encoding="utf-8").replace("Set Theme @theme.json", f"Set Theme {theme}"),
                encoding="utf-8",
            )
            proc = subprocess.run(["vhs", "validate", str(copy)], capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                failed += 1
                print(f"✗ {tape.relative_to(ROOT)}: vhs validate\n{proc.stdout}{proc.stderr}".rstrip())
    return failed


def compare(tape: Path, content: str) -> int:
    """Report whether a committed tape is what its lesson renders; 1 if not."""
    rel = tape.relative_to(ROOT)
    if not tape.exists():
        print(f"✗ {rel} is missing; run `task contributing:learn:tapes`")
        return 1
    if tape.read_text(encoding="utf-8") != content:
        print(f"✗ {rel} is stale; run `task contributing:learn:tapes`")
        return 1
    print(f"✓ {rel}")
    return 0


def strays(lessons: list[Path]) -> int:
    """Tapes under docs/learn/tapes/ whose lesson is gone; how many."""
    wanted = {tape_for(p).name for p in lessons}
    count = 0
    for stray in sorted(TAPES.glob("*.tape")):
        if stray.name not in wanted:
            print(f"✗ {stray.relative_to(ROOT)} has no lesson; delete it")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--page", metavar="NN", help="only lessons whose file name starts with NN")
    parser.add_argument("--check", action="store_true", help="report stale tapes and write nothing")
    args = parser.parse_args()

    found = [p for p in pages(args.page) if extract(p)]
    if not found:
        print("learntapes: no lesson with marked blocks under docs/learn/", file=sys.stderr)
        return 2

    problems = 0
    for page in found:
        tape = tape_for(page)
        content, bad = render(page)
        for line in bad:
            print(f"✗ {line}")
        problems += len(bad)
        if args.check:
            problems += compare(tape, content)
        else:
            TAPES.mkdir(parents=True, exist_ok=True)
            tape.write_text(content, encoding="utf-8")
            print(f"✓ {tape.relative_to(ROOT)}")

    if args.page is None:
        problems += strays(pages(None))
    problems += validate([tape_for(p) for p in found if tape_for(p).exists()])
    if problems:
        print(f"learntapes: {problems} problem(s)")
        return 1
    print(f"learntapes: {len(found)} tape(s) {'current' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
