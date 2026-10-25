#!/usr/bin/env python3
"""Run the commands in the course pages so a lesson cannot rot.

The lessons under docs/learn/ mark their runnable blocks with an HTML
comment on the line before the fence: `<!-- learn -->` for a block that
must exit 0, `<!-- learn: fails -->` for one that must exit non-zero,
and `<!-- learn: fails 1 -->` for one that must exit exactly that code
(the break-it step of most lessons promises a 1, a verdict, and would
otherwise pass on a 2, a check that could not run). Each page names its sandbox with
`<!-- learn-sandbox: demo -->` or `<!-- learn-sandbox: checkout -->` near
the top: `demo` is the repo `slopstopper demo` writes, committed once,
which is what every lesson but the last runs in (the suite lessons
install into it with `slopstopper install`); `checkout` (the default) is
a clone of this repository, for the lesson that edits the source. The clone carries the working tree's
uncommitted changes, so a lesson is checked against the Taskfile and CLI
you are about to commit rather than the ones you last did. The CLI that
runs this script goes on PATH, and each page's marked blocks run in
order with `sh -e`, the way a reader would type them. A page must leave
its sandbox clean (`git status --porcelain` empty), because the lessons
promise the next one starts from a fresh one.

Usage:
    python scripts/learncheck.py                 # every page under docs/learn/
    python scripts/learncheck.py --page 03       # pages whose name starts with 03
    python scripts/learncheck.py --page 06,07,08 # a few pages (what a CI shard runs)
    python scripts/learncheck.py --keep          # keep the sandboxes for a look

`task contributing:learn:check` runs it from the repo's venv; the `learn`
shards in `.github/workflows/ci-cli.yml` run it on every push to main,
nightly, and on a pull request that changes the course or this script.

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

# `<!-- learn -->`, `<!-- learn: fails -->` or `<!-- learn: fails N -->`,
# then a `sh` fence. The marker is on its own line directly before the
# fence, as the template says; a marker anywhere else is not a marker.
_BLOCK = re.compile(
    r"^<!-- learn(?:: (?P<mode>fails)(?: (?P<expect>[1-9]\d*))?)? -->\n```sh\n(?P<code>.*?)^```",
    re.M | re.S,
)
_SANDBOX = re.compile(r"^<!-- learn-sandbox: (?P<kind>demo|checkout) -->$", re.M)
# Any other line that starts like a marker is a typo (`fails: 1`, `fails 0`,
# a trailing space), and a typo must be loud rather than an unrun block.
_MARKER_LIKE = re.compile(r"^<!-- learn.*$", re.M)


@dataclass(frozen=True)
class Block:
    page: Path
    line: int
    code: str
    must_fail: bool
    expect: int | None = None  # the exact non-zero exit a `fails N` block promises

    @property
    def where(self) -> str:
        return f"{self.page.relative_to(ROOT)}:{self.line}"


def sandbox_kind(page: Path) -> str:
    """`demo` or `checkout`, from the page's marker; checkout when unmarked."""
    m = _SANDBOX.search(page.read_text(encoding="utf-8"))
    return m.group("kind") if m else "checkout"


def malformed_markers(page: Path) -> list[str]:
    """Marker-like lines the two patterns do not accept, with their line numbers."""
    text = page.read_text(encoding="utf-8")
    accepted = {m.start() for m in _BLOCK.finditer(text)} | {m.start() for m in _SANDBOX.finditer(text)}
    return [
        f"{page.relative_to(ROOT)}:{text.count(chr(10), 0, m.start()) + 1}: {m.group(0)}"
        for m in _MARKER_LIKE.finditer(text)
        if m.start() not in accepted
    ]


def extract(page: Path) -> list[Block]:
    text = page.read_text(encoding="utf-8")
    blocks = []
    for m in _BLOCK.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        expect = int(m.group("expect")) if m.group("expect") else None
        blocks.append(Block(page, line, m.group("code"), m.group("mode") == "fails", expect))
    return blocks


def pages(prefixes: str | None) -> list[Path]:
    """The lesson pages, or only those whose file name starts with one of
    the comma-separated `prefixes` (`03`, or `06,07,08` for a CI shard)."""
    found = sorted(p for p in LEARN.glob("*.md") if p.name[0].isdigit())
    wanted = [x.strip() for x in (prefixes or "").split(",") if x.strip()]
    if wanted:
        found = [p for p in found if any(p.name.startswith(w) for w in wanted)]
    return found


def git_identity(sandbox: Path) -> None:
    # Some lessons commit in the sandbox (the secrets lesson commits a
    # fake key to show that history is what is scanned); a CI runner has
    # no git identity, so the sandbox gets one of its own.
    for key, value in (("user.name", "learn"), ("user.email", "learn@slopstopper.dev")):
        subprocess.run(["git", "-C", str(sandbox), "config", key, value], check=True)


def link_node_modules(sandbox: Path) -> None:
    # The browser checks stage their specs next to node_modules, which is
    # gitignored; share this checkout's install rather than running npm
    # in every sandbox. The link is untracked, so the clean check ignores it.
    modules = ROOT / "node_modules"
    if modules.is_dir() and not (sandbox / "node_modules").exists():
        (sandbox / "node_modules").symlink_to(modules, target_is_directory=True)
        # `node_modules/` in .gitignore matches a directory, not a symlink,
        # so the link is excluded here or every page would read as dirty.
        with (sandbox / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
            exclude.write("node_modules\n")


def make_demo_sandbox(work: Path, env: dict[str, str]) -> Path:
    """The repo `slopstopper demo` writes, as one commit, which is where
    a reader runs the check lessons."""
    sandbox = work / "lantern"
    subprocess.run(["slopstopper", "--quiet", "demo", "--out", str(sandbox)], env=env, check=True)
    subprocess.run(["git", "-C", str(sandbox), "init", "--quiet", "-b", "main"], check=True)
    git_identity(sandbox)
    subprocess.run(["git", "-C", str(sandbox), "add", "--all"], check=True)
    subprocess.run(["git", "-C", str(sandbox), "commit", "--quiet", "-m", "lantern"], check=True)
    link_node_modules(sandbox)
    return sandbox


def make_sandbox(work: Path) -> Path:
    """A fresh clone of this repo, with the real origin so the checks that
    read it (docs-accuracy's repo links) behave as they do for a reader."""
    sandbox = work / "slopstopper"
    subprocess.run(["git", "clone", "--quiet", str(ROOT), str(sandbox)], check=True)
    origin = subprocess.run(
        ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    if origin:
        subprocess.run(["git", "-C", str(sandbox), "remote", "set-url", "origin", origin], check=True)
    git_identity(sandbox)
    snapshot_working_tree(sandbox)
    link_node_modules(sandbox)
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
    if block.must_fail and block.expect is not None:
        ok = result.returncode == block.expect
    else:
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
        want = str(block.expect) if block.expect is not None else ("non-zero" if block.must_fail else "0")
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
        print(f"✗ {page.relative_to(ROOT)} left its sandbox dirty; a lesson puts it back\n{indent(left)}")
        subprocess.run(["git", "checkout", "--quiet", "."], cwd=sandbox, check=False)
        subprocess.run(["git", "clean", "--quiet", "-fd"], cwd=sandbox, check=False)
    return failures


def preflight(selected: list[Path], per_page: dict[Path, list[Block]], env: dict[str, str]) -> str | None:
    """Why the harness cannot run, or None when it can."""
    if shutil.which("task") is None:
        return "`task` is not on PATH, and every lesson calls it (mise install)"
    bad = [line for page in selected for line in malformed_markers(page)]
    if bad:
        return "a marker-like line is not a marker (fix the typo, or it is a block that never runs):\n" + "\n".join("  " + b for b in bad)
    if sum(len(b) for b in per_page.values()) == 0:
        return f"no runnable blocks under {LEARN.relative_to(ROOT)} (mark one with <!-- learn -->)"
    if shutil.which("slopstopper", path=env["PATH"]) is None:
        return "no `slopstopper` next to this interpreter or on PATH (pip install -e ./cli)"
    return None


def run_pages(per_page: dict[Path, list[Block]], env: dict[str, str], keep: bool) -> int:
    """Run every page in the sandbox its marker names; return the failure count."""
    work = Path(tempfile.mkdtemp(prefix="learncheck-"))
    sandboxes: dict[str, Path] = {}
    total = sum(len(b) for b in per_page.values())
    print(f"learncheck: {total} blocks from {len(per_page)} pages, in sandboxes under {work}")
    failures = 0
    try:
        for page, blocks in per_page.items():
            kind = sandbox_kind(page)
            if kind not in sandboxes:
                sandboxes[kind] = make_demo_sandbox(work, env) if kind == "demo" else make_sandbox(work)
                print(f"learncheck: {kind} sandbox at {sandboxes[kind]}")
            failures += check_page(page, blocks, sandboxes[kind], env)
    finally:
        if keep:
            print(f"learncheck: sandboxes kept under {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--page", help="only pages whose file name starts with one of these, comma-separated (e.g. 03, or 06,07,08)")
    parser.add_argument("--keep", action="store_true", help="keep the sandboxes for inspection")
    args = parser.parse_args(argv)

    selected = pages(args.page)
    per_page = {page: extract(page) for page in selected}
    env = sandbox_env()
    problem = preflight(selected, per_page, env)
    if problem:
        print(f"learncheck: {problem}", file=sys.stderr)
        return 2
    failures = run_pages(per_page, env, args.keep)
    total = sum(len(b) for b in per_page.values())
    if failures:
        print(f"learncheck: {failures} problem(s) across {total} blocks: a block that did not do what its marker says, or a page that left the clone dirty")
        return 1
    print("learncheck: every block ran as its marker says, and every page left the clone clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
