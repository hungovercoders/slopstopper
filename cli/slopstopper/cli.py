"""Command dispatcher for the slopstopper CLI.

The slopstopper CLI is the single source of truth for every check in
the security / hygiene / reliability suite. Every workflow body, every
local `task ss:*` shim, and every CI step ultimately calls into one of
the subcommands below.

Subcommands:
  run <category>:<check>            Run a check, write reports under .ss/reports/.
  emit <category>:<check> --target  Post the report to a PR comment or main-
        {pr-comment, issue}         branch tracking issue (find-or-update).
  discover <check> --event <e>      Resolve pages.<check> via sitemap /
                                    changed-pages / explicit list, print
                                    comma-separated paths.
  config get <key> [<default>]      Read a value from .slopstopper.yml.
                                    Scalars print as-is; lists comma-joined;
                                    null/missing prints the default.
  templates list | path <n> | eject <n>
                                    Inspect / resolve / customise bundled
                                    Playwright specs, config, lighthouserc,
                                    server.js. Eject copies the bundled file
                                    into .ss/<name> for adopter editing.
  serve                             Run the bundled static server (with
                                    optional worker/headers.json auto-detect).
                                    execvp's into node so backgrounded
                                    `slopstopper serve &` gives bash the
                                    right PID for kill.
  checks list [--category <cat>] [--json]
                                    Walk the registry — show every check's
                                    name + one-line description. Useful for
                                    discoverability before running.
  doctor                            Verify install state: which external
                                    tools are present (node, gh, lizard,
                                    semgrep, gitleaks, trivy, docker).

Future: init, inspect.
"""

from __future__ import annotations

import argparse
import importlib
import json as _json
import os
import shutil
import subprocess
import sys

from slopstopper import (
    __version__,
    config,
    discovery,
    emit as emit_mod,
    output,
    templates,
)
from slopstopper.checks import REGISTRY


DOCS_URL = "https://slopstopper.dev"


# ── bare-invocation banner ───────────────────────────────────────


BANNER = f"""\
slopstopper {__version__}  ·  Portable code-quality suite

Usage:  slopstopper <command> [options]

Commands:
  run        Run a quality check (security, hygiene, reliability)
  emit       Post a check's report to a PR or main-branch issue
  discover   Resolve pages.<check> for a reliability check
  config     Read .slopstopper.yml values
  templates  Inspect / eject bundled templates
  serve      Run the bundled static server
  checks     List available checks
  doctor     Verify install + required tools

Quick start:
  slopstopper checks list             # see what's available
  slopstopper doctor                  # verify your install
  slopstopper run hygiene:docs-size   # run a check

Docs: {DOCS_URL}
"""


# ── main parser ──────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slopstopper",
        description=(
            "Portable code-quality suite — security, hygiene, reliability.\n\n"
            "Every check writes a report under .ss/reports/<category>/ and exits\n"
            "non-zero on failure. PR-comment / issue posting is decoupled via\n"
            "`slopstopper emit`. Templates (Playwright specs, lighthouserc,\n"
            "server.js) ship inside the wheel; adopters customise by ejecting\n"
            "a file into .ss/<name>.\n"
        ),
        epilog=(
            "Quick start:\n"
            "  slopstopper checks list             # see what's available\n"
            "  slopstopper doctor                  # verify your install\n"
            "  slopstopper run hygiene:docs-size   # run a check\n\n"
            f"Docs: {DOCS_URL}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"slopstopper {__version__}",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress decorative output (running/section/footer). Reports still write to disk.",
    )

    sub = parser.add_subparsers(dest="command")

    _add_run(sub)
    _add_emit(sub)
    _add_discover(sub)
    _add_config(sub)
    _add_templates(sub)
    _add_serve(sub)
    _add_checks(sub)
    _add_doctor(sub)

    return parser


def _add_run(sub) -> None:
    p = sub.add_parser(
        "run",
        help="Run a quality check by name",
        description=(
            "Run a check by its `<category>:<name>` key (see `slopstopper checks list`).\n"
            "Writes the report under .ss/reports/<category>/ and exits non-zero on failure.\n"
        ),
        epilog=(
            "Examples:\n"
            "  slopstopper run hygiene:docs-size\n"
            "  slopstopper run security:secrets\n"
            "  slopstopper run reliability:cwv -- --url https://example.com --prod\n"
            "  slopstopper run security:dast -- --target http://localhost:8080\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "check",
        help="Check name in 'category:name' form (e.g. hygiene:docs-size)",
    )
    # Extra args after the check name flow through to the check's own
    # parser. Only a couple of checks use this (e.g. security:dast
    # takes --target); most ignore.
    p.add_argument(
        "check_args",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded to the check (e.g. -- --target URL for dast)",
    )


def _add_emit(sub) -> None:
    p = sub.add_parser(
        "emit",
        help="Emit a previously-run check's report to GitHub",
        description=(
            "Post the check's report (already written by `slopstopper run …`) to\n"
            "either a PR comment (find-or-update by discriminator) or a main-branch\n"
            "tracking issue (create-or-update). Subprocess-invokes the `gh` CLI.\n"
        ),
        epilog=(
            "Examples:\n"
            "  slopstopper emit hygiene:docs-size --target pr-comment\n"
            "  slopstopper emit security:dast --target issue\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "check",
        help="Check name in 'category:name' form whose report to emit",
    )
    p.add_argument(
        "--target",
        required=True,
        choices=["pr-comment", "issue"],
        help="Where to send the report: pr-comment | issue",
    )


def _add_discover(sub) -> None:
    p = sub.add_parser(
        "discover",
        help="Resolve pages.<check> for a reliability check",
        description=(
            "Resolve the page list a reliability check should audit, using the\n"
            "resolution order: explicit list → sitemap.xml → changed pages (vs\n"
            "main). The event drives which mode `.slopstopper.yml` picks.\n"
            "Prints comma-separated paths to stdout; exit 2 if no path resolved.\n"
        ),
        epilog=(
            "Examples:\n"
            "  slopstopper discover smoke --event pr\n"
            "  slopstopper discover broken-links --event main\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "check",
        choices=discovery.CHECKS + ("broken-links",),
        help="Reliability check whose pages to resolve",
    )
    p.add_argument(
        "--event",
        choices=discovery.EVENTS,
        default="local",
        help="CI event that drives discovery mode (default: local)",
    )


def _add_config(sub) -> None:
    p = sub.add_parser(
        "config",
        help="Read values from .slopstopper.yml",
        description="Inspect values from .slopstopper.yml.\n",
    )
    config_sub = p.add_subparsers(dest="config_action", required=True)
    get = config_sub.add_parser(
        "get",
        help="Print the value at a dot-path key, or the default if missing",
        description=(
            "Read a dot-path key from .slopstopper.yml. Scalars print as-is;\n"
            "lists print comma-joined; null/missing keys print the default\n"
            "(or empty string).\n"
        ),
        epilog=(
            "Examples:\n"
            "  slopstopper config get node_version 20\n"
            "  slopstopper config get workflows.disabled\n"
            "  slopstopper config get urls.production\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    get.add_argument("key", help="Dot-path into .slopstopper.yml (e.g. workflows.disabled)")
    get.add_argument(
        "default",
        nargs="?",
        default="",
        help="Fallback printed when the key is missing or null (default: empty string)",
    )


def _add_templates(sub) -> None:
    p = sub.add_parser(
        "templates",
        help="Inspect / eject bundled templates",
        description=(
            "Bundled templates (Playwright specs, lighthouserc dev/prod, server.js,\n"
            "playwright.config.js) live inside the slopstopper-cli wheel. To\n"
            "customise, eject a template — `eject` copies it into `.ss/<name>`\n"
            "and the CLI's resolver prefers the override.\n"
        ),
    )
    sub2 = p.add_subparsers(dest="templates_action", required=True)
    sub2.add_parser(
        "list",
        help="List bundled templates and whether each is ejected to .ss/",
        description="List every bundled template, marking which ones are already ejected.\n",
        epilog="Example:\n  slopstopper templates list\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pa = sub2.add_parser(
        "path",
        help="Print the resolved path (override-or-bundled) for a template",
        description=(
            "Print the absolute path the CLI's templates resolver would use:\n"
            ".ss/<name> if ejected, else the wheel's package-data copy.\n"
        ),
        epilog="Example:\n  slopstopper templates path lighthouserc.json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pa.add_argument("name", help="Template name (see `slopstopper templates list`)")
    ej = sub2.add_parser(
        "eject",
        help="Copy the bundled template into .ss/<name> for customisation",
        description=(
            "Copy the bundled file into `.ss/<name>` so you can edit it. The\n"
            "CLI's templates resolver picks up the override on the next run.\n"
            "No-op if `.ss/<name>` already exists (customisations are preserved).\n"
        ),
        epilog="Example:\n  slopstopper templates eject lighthouserc.json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ej.add_argument("name", help="Template name (see `slopstopper templates list`)")


def _add_serve(sub) -> None:
    sub.add_parser(
        "serve",
        help="Run the bundled static server",
        description=(
            "Run the bundled static server. Auto-detects SERVE_ROOT\n"
            "(dist/client, dist, build, out, public, app — first match wins) and\n"
            "optionally applies headers from worker/headers.json if present.\n\n"
            "Replaces the slopstopper process via execvp(node), so a backgrounded\n"
            "`slopstopper serve &` gives bash the right PID via `$!` for later kill.\n"
        ),
        epilog=(
            "Environment:\n"
            "  PORT                    default 8080\n"
            "  SERVE_ROOT              explicit build-output dir\n"
            "  SS_SERVER_HEADERS       explicit JSON headers file\n\n"
            "Examples:\n"
            "  slopstopper serve\n"
            "  PORT=8000 SERVE_ROOT=dist/client slopstopper serve\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def _add_checks(sub) -> None:
    p = sub.add_parser(
        "checks",
        help="List available checks",
        description="Inspect what checks the installed CLI knows about.\n",
    )
    sub2 = p.add_subparsers(dest="checks_action", required=True)
    ls = sub2.add_parser(
        "list",
        help="List every check with its category + one-line description",
        description=(
            "Walk the REGISTRY and print each check's `<category>:<name>` key plus\n"
            "a one-line summary (first line of the check module's docstring).\n"
        ),
        epilog=(
            "Examples:\n"
            "  slopstopper checks list\n"
            "  slopstopper checks list --category security\n"
            "  slopstopper checks list --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ls.add_argument(
        "--category",
        choices=["security", "hygiene", "reliability"],
        help="Only show checks in this category",
    )
    ls.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the formatted table",
    )


def _add_doctor(sub) -> None:
    sub.add_parser(
        "doctor",
        help="Verify install + required external tools",
        description=(
            "Check that the external tools each slopstopper check needs are on\n"
            "PATH: node (Playwright/Lighthouse/server), gh (emit), lizard\n"
            "(complexity), semgrep (sast), gitleaks (secrets), trivy\n"
            "(dependencies), docker (dast). Reports each tool's install state.\n\n"
            "Exit 0 if everything required is installed (a missing tool whose\n"
            "check is in `workflows.disabled` doesn't count). Exit 1 if a\n"
            "required-and-enabled tool is missing.\n"
        ),
        epilog="Example:\n  slopstopper doctor\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


# ── main entry point ─────────────────────────────────────────────


# Top-level subcommand dispatch table. Each entry takes the parsed
# argparse Namespace and returns an exit code. Keeping the routing
# data-driven keeps main()'s cyclomatic complexity flat as the CLI
# gains subcommands.
_DISPATCHERS = {
    "run":       lambda a: _dispatch_run(a.check, a.check_args),
    "emit":      lambda a: _dispatch_emit(a.check, a.target),
    "discover":  lambda a: _dispatch_discover(a.check, a.event),
    "config":    lambda a: _dispatch_config_get(a.key, a.default),
    "templates": lambda a: _dispatch_templates(a.templates_action, getattr(a, "name", None)),
    "serve":     lambda a: _dispatch_serve(),
    "checks":    lambda a: _dispatch_checks_list(a.category, a.json),
    "doctor":    lambda a: _dispatch_doctor(),
}


def main(argv: list[str] | None = None) -> int:
    """Parse argv and dispatch.

    Bare `slopstopper` (no subcommand) prints the banner and exits 0 —
    no error, just a friendly landing page for first-time users.
    """
    parser = _build_parser()

    # Bare invocation → friendly banner. Argparse's `subparsers(required=True)`
    # would otherwise error out with a noisy stderr; we pre-check argv to
    # short-circuit before parsing.
    effective_argv = argv if argv is not None else sys.argv[1:]
    if not effective_argv:
        print(BANNER, end="")
        return 0

    args = parser.parse_args(argv)
    output.set_quiet(bool(getattr(args, "quiet", False)))

    dispatcher = _DISPATCHERS.get(args.command)
    if dispatcher is None:
        parser.error(f"unknown command: {args.command}")
        return 2
    return dispatcher(args)


# ── dispatchers ──────────────────────────────────────────────────


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
    # Drop the category, join remaining segments with underscores so multi-
    # segment names like `security:vulnerability:all` resolve to the
    # `vulnerability_all` module.
    parts = check_name.split(":")[1:]
    module_name = "slopstopper.checks." + "_".join(parts).replace("-", "_")
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


# ── checks list ──────────────────────────────────────────────────


def _check_summary(check_name: str) -> str:
    """First non-empty line of the check module's docstring, or ''."""
    # Drop the category, join remaining segments with underscores so multi-
    # segment names like `security:vulnerability:all` resolve to the
    # `vulnerability_all` module.
    parts = check_name.split(":")[1:]
    module_name = "slopstopper.checks." + "_".join(parts).replace("-", "_")
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return ""
    doc = module.__doc__ or ""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _dispatch_checks_list(category: str | None, as_json: bool) -> int:
    keys = sorted(REGISTRY)
    if category is not None:
        keys = [k for k in keys if k.split(":")[0] == category]

    entries = [{"name": k, "summary": _check_summary(k)} for k in keys]

    if as_json:
        print(_json.dumps(entries, indent=2))
        return 0

    if not entries:
        suffix = f" in category {category!r}" if category else ""
        print(f"No checks registered{suffix}.")
        return 0

    width = max(len(e["name"]) for e in entries)
    for e in entries:
        print(f"  {e['name']:<{width}}  {e['summary']}")
    return 0


# ── doctor ───────────────────────────────────────────────────────


# Each entry: tool name → (check-name-that-needs-it, install hint).
# A "check-name-that-needs-it" of None means the tool is needed by the
# CLI itself (gh for emit, node for several reliability checks).
#
# Note on lizard: it used to appear here as an external binary, which
# was misleading — `brew install lizard` ships lz4's lizard (different
# tool), and the real Python lizard had to be `pipx inject`ed into
# the slopstopper-cli venv before hygiene:complexity worked. lizard
# is now a runtime dependency of slopstopper-cli (see pyproject.toml),
# so it's always in the venv that `python -m lizard` resolves against.
# Doctor no longer needs to check for it.
_DOCTOR_TOOLS: list[tuple[str, str | None, str]] = [
    ("node", None, "Install Node.js (https://nodejs.org/) — required by Playwright, Lighthouse, server"),
    ("gh", None, "Install GitHub CLI (https://cli.github.com/) — required by `slopstopper emit`"),
    ("semgrep", "security:sast", "pip install --user semgrep  or  brew install semgrep"),
    ("gitleaks", "security:secrets", "brew install gitleaks  or  apt-get install gitleaks"),
    ("trivy", "security:vulnerability:all", "brew install aquasecurity/trivy/trivy  or  see https://trivy.dev"),
    ("docker", "security:dast", "Install Docker Desktop (https://docs.docker.com/get-docker/)"),
]


def _tool_version(tool: str) -> str:
    """Best-effort short version string for a tool. Returns '' if unknown."""
    try:
        result = subprocess.run(
            [tool, "--version"], capture_output=True, text=True, check=False, timeout=5
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    text = (result.stdout or result.stderr or "").strip().splitlines()
    return text[0] if text else ""


def _disabled_workflows() -> set[str]:
    """Set of disabled workflow filenames from .slopstopper.yml."""
    raw = config.get("workflows.disabled", [])
    if not isinstance(raw, list):
        return set()
    return {str(w) for w in raw}


def _check_is_disabled(check_name: str, disabled: set[str]) -> bool:
    """True if the workflow that fronts `check_name` is in workflows.disabled.

    Conservative match: `hygiene:complexity` → ss-hygiene-complexity-check.yml.
    """
    if ":" not in check_name:
        return False
    category, action = check_name.split(":", 1)
    workflow = f"ss-{category}-{action}-check.yml"
    return workflow in disabled


def _dispatch_doctor() -> int:
    """Verify external tools are installed; exit 1 if a required one is missing."""
    output.status("🩺", "slopstopper doctor — checking external tools")
    output.separator()

    disabled = _disabled_workflows()
    missing_required = 0

    for tool, needed_by, hint in _DOCTOR_TOOLS:
        path = shutil.which(tool)
        if path:
            version = _tool_version(tool)
            extra = f" — {version}" if version else ""
            output.success(f"{tool:<10} found at {path}{extra}")
            continue

        # Missing.
        if needed_by and _check_is_disabled(needed_by, disabled):
            output.info(
                f"{tool:<10} not installed (only needed by {needed_by}, "
                f"which is disabled in .slopstopper.yml — skipping)"
            )
            continue

        # Required and not disabled.
        scope = needed_by if needed_by else "the CLI itself"
        output.error(f"{tool:<10} not installed — needed by {scope}")
        output._emit(f"             {hint}")
        missing_required += 1

    output.separator()
    if missing_required == 0:
        output.success("All required tools available.")
        return 0
    output.error(f"{missing_required} required tool(s) missing — see hints above.")
    return 1
