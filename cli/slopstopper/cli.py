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
  config get <key> [<default>]      — read a value from .slopstopper.yml.
                                      Scalars print as-is; lists print
                                      comma-joined; null/missing prints the
                                      default (or empty string). Drop-in
                                      replacement for the bash-side
                                      .ss/scripts/load_config.py CLI shim.
  templates list                    — list bundled templates and whether
                                      each one is ejected to .ss/.
  templates path <name>             — print the absolute path the resolver
                                      would use (override-or-bundled).
  templates eject <name>            — copy the bundled template into .ss/
                                      so the adopter can customise it.
  serve                             — run the bundled static server
                                      (`.ss/server.js` override wins) via
                                      node. Replaces the process so a
                                      backgrounded `slopstopper serve &`
                                      gives bash the right PID for kill.

Future: init, inspect.
"""

from __future__ import annotations

import argparse
import importlib
import os
import shutil
import sys

from slopstopper import __version__, config, discovery, emit as emit_mod, templates
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

    config_parser = sub.add_parser(
        "config",
        help="Read values from .slopstopper.yml",
    )
    config_sub = config_parser.add_subparsers(dest="config_action", required=True)
    config_get = config_sub.add_parser(
        "get",
        help="Print the value at a dot-path key, or the default if missing",
    )
    config_get.add_argument("key", help="Dot-path into .slopstopper.yml (e.g. workflows.disabled)")
    config_get.add_argument(
        "default",
        nargs="?",
        default="",
        help="Fallback printed when the key is missing or null (default: empty string)",
    )

    templates_parser = sub.add_parser(
        "templates",
        help="Inspect and eject bundled templates (Playwright specs/config, lighthouserc).",
    )
    templates_sub = templates_parser.add_subparsers(dest="templates_action", required=True)
    templates_sub.add_parser(
        "list",
        help="List bundled template names and whether each is ejected to .ss/",
    )
    templates_path = templates_sub.add_parser(
        "path",
        help="Print the resolved path (override-or-bundled) for a template",
    )
    templates_path.add_argument("name", help="Template name (see `slopstopper templates list`)")
    templates_eject = templates_sub.add_parser(
        "eject",
        help="Copy the bundled template into .ss/<name> for customisation",
    )
    templates_eject.add_argument("name", help="Template name (see `slopstopper templates list`)")

    sub.add_parser(
        "serve",
        help=(
            "Run the bundled static server (auto-detect SERVE_ROOT, optional "
            "SS_SERVER_HEADERS). Replaces the process so backgrounded "
            "`slopstopper serve &` gives bash the right PID for kill."
        ),
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        return _dispatch_run(args.check, args.check_args)
    if args.command == "emit":
        return _dispatch_emit(args.check, args.target)
    if args.command == "discover":
        return _dispatch_discover(args.check, args.event)
    if args.command == "config":
        if args.config_action == "get":
            return _dispatch_config_get(args.key, args.default)
    if args.command == "templates":
        return _dispatch_templates(args.templates_action, getattr(args, "name", None))
    if args.command == "serve":
        return _dispatch_serve()

    parser.error(f"unknown command: {args.command}")
    return 2


def _dispatch_run(check_name: str, check_args: list[str]) -> int:
    if check_name not in REGISTRY:
        print(f"❌ unknown check: {check_name}", file=sys.stderr)
        print(f"   known checks: {', '.join(sorted(REGISTRY))}", file=sys.stderr)
        return 2
    return REGISTRY[check_name](check_args)


def _dispatch_config_get(key: str, default: str) -> int:
    """Print the value at `key`, matching the bash load_config.py shape.

    Scalars print as-is. Lists print comma-joined. Missing / null
    values print the `default` argument (which itself defaults to an
    empty string).
    """
    value = config.get(key, default)
    if value is None:
        print("")
    elif isinstance(value, list):
        print(",".join(str(v) for v in value))
    else:
        print(value)
    return 0


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


def _dispatch_serve() -> int:
    """Replace the current process with `node <bundled or ejected server.js>`.

    Using execvp (not subprocess) means a backgrounded `slopstopper serve
    &` in bash gets the right PID via `$!` — bash sees node, and
    `kill $SERVER_PID` actually stops the listener.
    """
    if not shutil.which("node"):
        print("❌ node is not available — install Node.js to run the local server", file=sys.stderr)
        return 1
    server_path = templates.template_path(templates.SERVER_JS_NAME)
    if not server_path.exists():
        print(f"❌ Bundled server.js not found at {server_path}", file=sys.stderr)
        return 1
    os.execvp("node", ["node", str(server_path)])
    return 1  # unreachable — execvp doesn't return on success


def _dispatch_templates(action: str, name: str | None) -> int:
    """Route the `templates {list, path, eject}` subcommands."""
    if action == "list":
        for n in templates.list_templates():
            mark = "(ejected → .ss/)" if templates.is_ejected(n) else "(bundled)"
            print(f"{n}  {mark}")
        return 0
    if action == "path":
        try:
            print(templates.template_path(name))  # type: ignore[arg-type]
        except KeyError:
            print(f"❌ unknown template: {name}", file=sys.stderr)
            print(
                f"   known templates: {', '.join(templates.list_templates())}", file=sys.stderr
            )
            return 2
        return 0
    if action == "eject":
        try:
            dest, was_new = templates.eject(name)  # type: ignore[arg-type]
        except KeyError:
            print(f"❌ unknown template: {name}", file=sys.stderr)
            print(
                f"   known templates: {', '.join(templates.list_templates())}", file=sys.stderr
            )
            return 2
        if was_new:
            print(f"✅ ejected to {dest}")
        else:
            print(f"ℹ️  {dest} already exists — left in place (will keep overriding the bundle)")
        return 0
    print(f"❌ unknown templates action: {action}", file=sys.stderr)
    return 2


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
