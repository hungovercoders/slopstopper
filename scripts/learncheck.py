#!/usr/bin/env python3
"""Run the commands in the course pages so a lesson cannot rot.

The lessons under docs/learn/ mark their runnable blocks with an HTML
comment on the line before the fence: `<!-- learn -->` for a block that
must exit 0, `<!-- learn: fails -->` for one that must exit non-zero
(the break-it step of most lessons). This script clones the repository
into a scratch directory, which is the sandbox the syllabus gives a
reader until the lessons move onto `slopstopper demo` (#486), commits the working tree's
uncommitted changes into that clone so a lesson is checked against the
Taskfile and CLI you are about to commit rather than the ones you last
did, puts the CLI that runs this script on PATH, and runs each page's
marked blocks in order with `sh -e`, the way a reader would type them.
A page must leave the clone clean (`git status --porcelain` empty),
because the lessons promise the next one starts from a fresh checkout.

Usage:
    python scripts/learncheck.py                 # every page under docs/learn/
    python scripts/learncheck.py --page 03       # pages whose name starts with 03
    python scripts/learncheck.py --keep          # keep the scratch clone for a look

`task contributing:learn:check` runs it from the repo's venv; the `learn`
job in `.github/workflows/ci-cli.yml` runs it on every change to the
course or the CLI.

Exit codes follow the suite's contract: 0 every block did what its
marker says, 1 a block did not (or a page left the clone dirty), 2 the
harness could not run (no marked blocks, no `task` on PATH).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARN = ROOT / "docs" / "learn"

# `<!-- learn -->` or `<!-- learn: fails -->`, then a `sh` fence. The
# marker is on its own line directly before the fence, as the template
# says; a marker anywhere else is not a marker.
_BLOCK = re.compile(
    r"^<!-- learn(?:: (?P<mode>fails))? -->\n```sh\n(?P<code>.*?)^```",
    re.M | re.S,
)


@dataclass(frozen=True)
class Block:
    page: Path
    line: int
    code: str
    must_fail: bool

    @property
    def where(self) -> str:
        return f"{self.page.relative_to(ROOT)}:{self.line}"


def extract(page: Path) -> list[Block]:
    text = page.read_text(encoding="utf-8")
    blocks = []
    for m in _BLOCK.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        blocks.append(Block(page, line, m.group("code"), m.group("mode") == "fails"))
    return blocks


def pages(prefix: str | None) -> list[Path]:
    found = sorted(p for p in LEARN.glob("*.md") if p.name[0].isdigit())
    if prefix:
        found = [p for p in found if p.name.startswith(prefix)]
    return found


def make_sandbox(keep: bool) -> Path:
    """A fresh clone of this repo, with the real origin so the checks that
    read it (docs-accuracy's repo links) behave as they do for a reader."""
    work = Path(tempfile.mkdtemp(prefix="learncheck-"))
    sandbox = work / "slopstopper"
    subprocess.run(["git", "clone", "--quiet", str(ROOT), str(sandbox)], check=True)
    origin = subprocess.run(
        ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    if origin:
        subprocess.run(["git", "-C", str(sandbox), "remote", "set-url", "origin", origin], check=True)
    # Some lessons commit in the clone (the secrets lesson commits a fake
    # key to show that history is what is scanned); a CI runner has no
    # git identity, so the clone gets one of its own.
    for key, value in (("user.name", "learn"), ("user.email", "learn@slopstopper.dev")):
        subprocess.run(["git", "-C", str(sandbox), "config", key, value], check=True)
    snapshot_working_tree(sandbox)
    # The browser checks stage their specs next to node_modules, which is
    # gitignored; share this checkout's install rather than running npm
    # in every clone. The link is untracked, so the clean check ignores it.
    modules = ROOT / "node_modules"
    if modules.is_dir():
        (sandbox / "node_modules").symlink_to(modules, target_is_directory=True)
        # `node_modules/` in .gitignore matches a directory, not a symlink,
        # so the link is excluded here or every page would read as dirty.
        with (sandbox / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
            exclude.write("node_modules\n")
    if keep:
        print(f"learncheck: scratch clone kept at {sandbox}")
    return sandbox


def snapshot_working_tree(sandbox: Path) -> None:
    """Commit this checkout's uncommitted changes into the clone.

    `git clone` copies HEAD, but the lessons are read from the working
    tree and the editable CLI runs working-tree code, so a lesson checked
    before its commit would otherwise run against a stale Taskfile or
    check. Tracked changes travel as a patch, untracked files (a new
    lesson, say) are copied, and the result is one commit on top of HEAD,
    so the clone starts clean and `git checkout <file>` in a lesson still
    restores what the reader would see.
    """
    patch = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--binary", "HEAD"], capture_output=True, check=True,
    ).stdout
    if patch:
        subprocess.run(["git", "-C", str(sandbox), "apply", "--binary"], input=patch, check=True)
    untracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard", "-z"],
        capture_output=True, text=True, check=True,
    ).stdout.split("\0")
    for rel in filter(None, untracked):
        target = sandbox / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    subprocess.run(["git", "-C", str(sandbox), "add", "--all"], check=True)
    staged = subprocess.run(["git", "-C", str(sandbox), "diff", "--cached", "--quiet"], check=False)
    if staged.returncode != 0:
        subprocess.run(
            ["git", "-C", str(sandbox), "commit", "--quiet", "-m", "learncheck: snapshot of the working tree"],
            check=True,
        )


def sandbox_env() -> dict[str, str]:
    """The lessons' environment: the CLI this interpreter belongs to first.

    `sys.executable` is kept as given, not resolved: in a venv it is a
    symlink to the base interpreter, and resolving it would put that
    interpreter's bin on PATH instead of the venv's, where `slopstopper`
    actually is.
    """
    env = dict(os.environ)
    cli_bin = str(Path(sys.executable).parent)
    env["PATH"] = cli_bin + os.pathsep + env.get("PATH", "")
    env["NO_COLOR"] = "1"
    return env


def run_block(block: Block, sandbox: Path, env: dict[str, str]) -> tuple[bool, str]:
    result = subprocess.run(
        ["sh", "-e"], cwd=sandbox, env=env, input=block.code,
        capture_output=True, text=True, check=False,
    )
    failed = result.returncode != 0
    ok = failed if block.must_fail else not failed
    output = (result.stdout + result.stderr).rstrip("\n")
    return ok, f"exit {result.returncode}\n{output}"


def dirty(sandbox: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"], cwd=sandbox, capture_output=True, text=True, check=False,
    ).stdout.strip()


def indent(text: str) -> str:
    return "\n".join("    " + line for line in text.splitlines())


def stop_leftovers(sandbox: Path) -> list[str]:
    """Stop every process a page's pid files still name.

    A lesson tracks a background server by a pid file under `scratch/`
    and kills it in a later block. When a block fails first, `sh -e`
    never reaches that kill, and the dirty-tree cleanup below would
    delete the pid file while the server kept its port, so the next
    lesson's server could not bind. Stop them here, before cleanup.
    """
    stopped = []
    for pid_file in sorted((sandbox / "scratch").glob("*.pid")):
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
        except (ValueError, ProcessLookupError, PermissionError):
            continue
        stopped.append(f"{pid_file.name} (pid {pid})")
    return stopped


def check_page(page: Path, blocks: list[Block], sandbox: Path, env: dict[str, str]) -> int:
    failures = 0
    for block in blocks:
        ok, detail = run_block(block, sandbox, env)
        want = "non-zero" if block.must_fail else "0"
        if ok:
            print(f"✓ {block.where}")
            continue
        failures += 1
        print(f"✗ {block.where} (expected exit {want})\n{indent(detail)}")
    for name in stop_leftovers(sandbox):
        print(f"  stopped a server the page left running: {name}")
    left = dirty(sandbox)
    if left:
        failures += 1
        print(f"✗ {page.relative_to(ROOT)} left the checkout dirty; a lesson puts it back\n{indent(left)}")
        subprocess.run(["git", "checkout", "--quiet", "."], cwd=sandbox, check=False)
        subprocess.run(["git", "clean", "--quiet", "-fd"], cwd=sandbox, check=False)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--page", help="only pages whose file name starts with this (e.g. 03)")
    parser.add_argument("--keep", action="store_true", help="keep the scratch clone for inspection")
    args = parser.parse_args(argv)

    if shutil.which("task") is None:
        print("learncheck: `task` is not on PATH, and every lesson calls it (mise install)", file=sys.stderr)
        return 2
    selected = pages(args.page)
    per_page = {page: extract(page) for page in selected}
    total = sum(len(b) for b in per_page.values())
    if total == 0:
        print(f"learncheck: no runnable blocks under {LEARN.relative_to(ROOT)} (mark one with <!-- learn -->)", file=sys.stderr)
        return 2

    env = sandbox_env()
    if shutil.which("slopstopper", path=env["PATH"]) is None:
        print("learncheck: no `slopstopper` next to this interpreter or on PATH (pip install -e ./cli)", file=sys.stderr)
        return 2
    sandbox = make_sandbox(args.keep)
    print(f"learncheck: {total} blocks from {len(selected)} pages, in a clone at {sandbox}")
    failures = 0
    try:
        for page, blocks in per_page.items():
            failures += check_page(page, blocks, sandbox, env)
    finally:
        if not args.keep:
            shutil.rmtree(sandbox.parent, ignore_errors=True)
    if failures:
        print(f"learncheck: {failures} problem(s) across {total} blocks: a block that did not do what its marker says, or a page that left the clone dirty")
        return 1
    print("learncheck: every block ran as its marker says, and every page left the clone clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
