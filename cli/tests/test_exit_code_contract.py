"""Guard: every check honours the exit-code contract in `slopstopper.checks`.

    0 — ran, nothing to fail on (including a graceful skip)
    1 — ran, the repo failed it
    2 — could not run: missing tool, missing input, bad argument

The contract is the CLI's API — workflows gate on it, `emit --status`
derives pass/fail from it, and adopters script against it. It used to be
documented per check and honoured unevenly: one check returned 2 for
findings, two returned 0 unconditionally with the real verdict in a
Python heredoc inside YAML, and nine silently dropped any arguments
they were given.

Two things are checked here. Every check module's docstring declares an
`Exit codes:` block naming 0 and 1, and names 2 if — and only if — the
module can return it (found by walking the AST, so a comment can't fake
it). And the checks that take no arguments reject them with 2 rather
than running as if nothing was said.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from slopstopper.checks import REGISTRY


CHECKS = sorted(REGISTRY)


def _module(check: str):
    return inspect.getmodule(REGISTRY[check])


# The `_contract` helpers that can hand a check a 2 to return.
CONTRACT_HELPERS_RETURNING_TWO = frozenset(
    {"reject_extra_args", "refuse_unsafe_url", "runner_exit", "scan_incomplete"}
)


def _returns_two(check: str) -> bool:
    """True if any function in the check's module can return 2.

    A literal `return 2` / `return EXIT_CANNOT_RUN`, or a call to one of
    the `_contract` helpers that yield 2 (whose result the check returns).
    """
    source = Path(inspect.getsourcefile(_module(check))).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name in CONTRACT_HELPERS_RETURNING_TWO:
                return True
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value
        if isinstance(value, ast.Constant) and value.value == 2:
            return True
        if isinstance(value, ast.Name) and value.id == "EXIT_CANNOT_RUN":
            return True
    return False


def test_a_crash_in_any_check_is_could_not_run(monkeypatch, isolated_cwd):
    """The dispatcher, not each check, owns the crash → 2 mapping."""
    from slopstopper import cli

    def boom(_args):
        raise RuntimeError("boom")

    monkeypatch.setitem(cli.REGISTRY, "hygiene:test-boom", boom)
    assert cli.main(["run", "hygiene:test-boom"]) == 2


def _exit_codes_block(check: str) -> str:
    doc = _module(check).__doc__ or ""
    m = re.search(r"^Exit codes[^\n]*\n((?:[ \t]+.*\n?)+)", doc, re.M)
    assert m, f"{check}: module docstring has no `Exit codes:` block"
    return m.group(1)


@pytest.mark.parametrize("check", CHECKS)
def test_docstring_declares_zero_and_one(check):
    block = _exit_codes_block(check)
    assert re.search(r"^\s+0 —", block, re.M), f"{check}: `Exit codes:` block does not name 0"
    assert re.search(r"^\s+1 —", block, re.M) or "always" in block, (
        f"{check}: `Exit codes:` block does not name 1 (or say the check is advisory)"
    )


@pytest.mark.parametrize("check", CHECKS)
def test_docstring_names_two_iff_the_code_can_return_it(check):
    declared = bool(re.search(r"^\s+2 —", _exit_codes_block(check), re.M))
    possible = _returns_two(check)
    assert declared == possible, (
        f"{check}: docstring {'names' if declared else 'omits'} exit 2 but the code "
        f"{'can' if possible else 'cannot'} return it"
    )


# ── the nine that take no arguments ──────────────────────────────

NO_ARG_CHECKS = [
    "hygiene:complexity",
    "hygiene:csp-exceptions",
    "hygiene:docs-accuracy",
    "hygiene:docs-size",
    "hygiene:docs-structure",
    "hygiene:entry-files",
    "security:sast",
    "security:secrets",
    "security:vulnerability:all",
]


@pytest.mark.parametrize("check", NO_ARG_CHECKS)
def test_a_check_with_no_parser_rejects_arguments(check, isolated_cwd, capsys):
    """`slopstopper run hygiene:complexity -- --max-ccn 5` must not run with
    the default and say nothing."""
    rc = REGISTRY[check](["--max-ccn", "5"])
    assert rc == 2
    out = capsys.readouterr().out
    assert "takes no arguments" in out
    assert "--max-ccn 5" in out


@pytest.mark.parametrize("check", CHECKS)
def test_every_check_accepts_an_empty_argument_list(check):
    """The dispatcher always passes a list; `[]` and `None` must both mean "no args"."""
    sig = inspect.signature(REGISTRY[check])
    params = list(sig.parameters.values())
    assert len(params) == 1, f"{check}: run() should take exactly one parameter"
    assert params[0].default is None, f"{check}: run()'s parameter should default to None"
