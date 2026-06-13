"""Command dispatcher for the slopstopper CLI.

Subcommands today:
  run <check>                       — run a check, write reports under .ss/reports/
  emit <check> --target {pr-comment,issue}
                                    — post the report MD to the current PR
                                      or create/update a tracking issue on main
  discover <check> --event=<event>  — resolve pages.<check> via sitemap /
                                      changed-pages / explicit list and print
                                      a comma-separated path list to stdout
                                      (drop-in replacement for the bash-side
                                      .ss/scripts/discover-pages.py).

Future: init, inspect.
"""

from __future__ import annotations

import argparse
import importlib
import sys

from slopstopper import __version__, discovery, emit as emit_mod
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

    emit_parser = sub.add_parser(
        "emit",
        help="Emit a previously-run check's report to GitHub (PR comment / issue)",
    )
    emit_parser.add_argument(
        "check",
        help="Check name in 'category:name' form whose report to emit",
    )
    emit_parser.add_argument(
        "--target",
        required=True,
        choices=["pr-comment", "issue"],
        help="Where to send the report",
    )

    discover_parser = sub.add_parser(
        "discover",
        help="Resolve pages.<check> for a reliability check and print the list to stdout",
    )
    # Accept both `broken-links` (hyphen, slopstopper-style) and
    # `broken_links` (underscore, matches the bash script's args) so this
    # is a strict superset of `.ss/scripts/discover-pages.py`'s CLI.
    discover_parser.add_argument(
        "check",
        choices=discovery.CHECKS + ("broken-links",),
        help="Reliability check whose pages to resolve",
    )
    discover_parser.add_argument(
        "--event",
        choices=discovery.EVENTS,
        default="local",
        help="CI event that drives discovery mode (default: local)",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        return _dispatch_run(args.check, args.check_args)
    if args.command == "emit":
        return _dispatch_emit(args.check, args.target)
    if args.command == "discover":
        return _dispatch_discover(args.check, args.event)

    parser.error(f"unknown command: {args.command}")
    return 2


def _dispatch_run(check_name: str, check_args: list[str]) -> int:
    if check_name not in REGISTRY:
        print(f"❌ unknown check: {check_name}", file=sys.stderr)
        print(f"   known checks: {', '.join(sorted(REGISTRY))}", file=sys.stderr)
        return 2
    return REGISTRY[check_name](check_args)


def _dispatch_discover(check_name: str, event: str) -> int:
    """Resolve pages for `check_name` under `event` and print comma-joined paths.

    Mirrors the bash `.ss/scripts/discover-pages.py` exit codes:
      0 — at least one path resolved (printed to stdout)
      1 — internal error (logged to stderr)
      2 — no path resolved (nothing printed)
    """
    normalised = check_name.replace("-", "_")
    try:
        paths = discovery.discover(normalised, event)
    except Exception as e:  # noqa: BLE001
        print(f"❌ internal discovery error: {e}", file=sys.stderr)
        return 1
    if not paths:
        return 2
    print(",".join(paths))
    return 0


def _dispatch_emit(check_name: str, target: str) -> int:
    """Look up the check's META dict (from its module) and emit."""
    if check_name not in REGISTRY:
        print(f"❌ unknown check: {check_name}", file=sys.stderr)
        return 2
    module_name = "slopstopper.checks." + check_name.split(":")[1].replace("-", "_")
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ cannot import {module_name}: {e}", file=sys.stderr)
        return 2
    meta = getattr(module, "META", None)
    if not meta:
        print(
            f"❌ {check_name} has no META — emit is not yet wired up for this check",
            file=sys.stderr,
        )
        return 2
    return emit_mod.emit(target, meta)
