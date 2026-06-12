"""Command dispatcher for the slopstopper CLI.

Today: one subcommand, `run <check>`, which dispatches to the check
registry under `slopstopper.checks`. Future: `init`, `inspect`, `emit`.
"""

from __future__ import annotations

import argparse
import sys

from slopstopper import __version__
from slopstopper.checks import REGISTRY


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="slopstopper",
        description="Slopstopper quality suite CLI.",
    )
    parser.add_argument("--version", action="version", version=f"slopstopper {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a quality check by name")
    run_parser.add_argument(
        "check",
        help="Check name in 'category:name' form (e.g. hygiene:docs-size)",
    )
    # Extra args after the check name flow through to the check's own
    # parser. Only a couple of checks use this (e.g. security:dast
    # takes --target); most ignore.
    run_parser.add_argument(
        "check_args",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded to the check (e.g. --target URL for dast)",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        return _dispatch_run(args.check, args.check_args)

    parser.error(f"unknown command: {args.command}")
    return 2


def _dispatch_run(check_name: str, check_args: list[str]) -> int:
    if check_name not in REGISTRY:
        print(f"❌ unknown check: {check_name}", file=sys.stderr)
        print(f"   known checks: {', '.join(sorted(REGISTRY))}", file=sys.stderr)
        return 2
    return REGISTRY[check_name](check_args)
