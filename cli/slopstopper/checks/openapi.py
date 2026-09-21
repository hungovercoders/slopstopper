"""OpenAPI spec drift audit (in-CLI implementation).

The API-shaped analogue of `hygiene:docs-accuracy`. That check catches a
doc that references a file which moved; this one catches a spec that has
stopped describing the API it documents. Both are the same failure —
documentation that quietly became fiction — on different surfaces.

Two directions, because those are the two this can answer honestly
without introspecting the app's routes:

  committed vs served
      When `api.openapi.spec` is a file in the repo and
      `api.openapi.served_spec` is the URL the running API publishes its
      spec at, compare the two operation sets. A difference means the
      committed artifact is stale against what is actually deployed.
      This is the headline check: no probing, no guessing, no false
      positives.

  documented vs reachable
      Every documented path that takes no parameters is probed. A 404 or
      5xx means the spec describes a route that isn't there.

Paths with parameters (`/users/{id}`) are counted and reported but not
probed: a 404 from one may mean "route missing" or merely "no such id",
and the check cannot tell those apart. Reporting both as failures would
train people to ignore it.

Detecting *undocumented* routes — the other half of drift — is out of
scope. It needs framework-specific route introspection (FastAPI, Express
and Spring each expose their routing differently), which is a different
and much larger check.

**JSON specs only.** Parsing YAML would mean a third-party dependency,
and slopstopper-cli ships none. Most frameworks serve the JSON form at
`/openapi.json`; point the check there. A YAML spec is a graceful skip
with that guidance, not a failure.

CLI surface:
  slopstopper run hygiene:openapi -- --url URL [--spec openapi.json]
        [--served-spec https://api.example.com/openapi.json]
        [--no-probe] [--ignore /internal/*]

Stdlib-only (urllib + json). Writes
.ss/reports/openapi/openapi-report.{md,json}.

Configuration (.slopstopper.yml — all optional):

    api:
      openapi:
        spec:           # file or URL — shared with security:dast
        served_spec:    # URL the live API serves its spec at
        probe_paths: true
        ignore_paths: []

See .slopstopper.yml.example for the canonical schema.

Exit codes:
  0 — spec and API agree, or nothing configured / the spec is YAML
      (graceful skip)
  1 — drift detected, the spec is unreadable or malformed, or an
      unsafe-scheme URL was supplied
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from slopstopper import config, output


REPORT_DIR = Path(".ss/reports/openapi")
REPORT_MD = REPORT_DIR / "openapi-report.md"
REPORT_JSON = REPORT_DIR / "openapi-report.json"
USER_AGENT = "SlopStopper-OpenAPI-Check/1.0"
TIMEOUT_SECONDS = 15
ALLOWED_SCHEMES = ("http", "https")

# Keys OpenAPI/Swagger use to declare the spec version. One must be present
# for the document to be a spec rather than arbitrary JSON.
VERSION_KEYS = ("openapi", "swagger")

# Methods worth probing / comparing. `parameters` and `summary` also live
# under a path item, and are not operations.
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")

# Consumed by `slopstopper emit hygiene:openapi --target pr-comment`.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "📘 OpenAPI",
}


# ── safety ───────────────────────────────────────────────────────


def _require_safe_url(url: str) -> None:
    """Reject any URL whose scheme isn't http/https (blocks file:// SSRF)."""
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"OpenAPI check refuses scheme {scheme!r} (only http/https allowed). url={url!r}"
        )


def _fetch(url: str) -> tuple[int, str]:
    """GET the URL. Returns (status, body). A 4xx/5xx is data, not an error."""
    _require_safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # nosec B310
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body


def _probe_status(url: str) -> int | None:
    """Status code for a probe, or None when the request never landed."""
    try:
        status, _ = _fetch(url)
        return status
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


# ── spec loading ─────────────────────────────────────────────────


def _spec_is_url(spec: str) -> bool:
    return spec.startswith("http://") or spec.startswith("https://")


def _looks_like_yaml(spec: str) -> bool:
    """A spec we can't read, identified before trying to parse it."""
    return spec.lower().endswith((".yaml", ".yml"))


def _load_spec_text(spec: str) -> tuple[str | None, str | None]:
    """(text, error). Reads a URL or a repo-relative file."""
    if _spec_is_url(spec):
        try:
            status, body = _fetch(spec)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            return None, f"could not fetch {spec}: {type(e).__name__}: {e}"
        if status >= 400:
            return None, f"{spec} returned HTTP {status}"
        return body, None

    path = Path(spec)
    if not path.is_file():
        return None, f"spec file not found: {spec}"
    return path.read_text(encoding="utf-8", errors="replace"), None


def _parse_spec(text: str, label: str) -> tuple[dict | None, str | None]:
    """(document, error). JSON only — see the module docstring."""
    try:
        document = json.loads(text)
    except ValueError as e:
        return None, f"{label} is not valid JSON: {e}"
    if not isinstance(document, dict):
        return None, f"{label} is valid JSON but not an object"
    return document, None


def _validate_shape(document: dict, label: str) -> list[str]:
    """The minimum that makes a JSON document an OpenAPI spec."""
    issues = []
    if not any(key in document for key in VERSION_KEYS):
        issues.append(
            f"{label} has no `openapi` or `swagger` version key — is it really a spec?"
        )
    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths:
        issues.append(f"{label} declares no `paths`")
    return issues


# ── operation sets ───────────────────────────────────────────────


def _is_ignored(path: str, ignore_paths: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in ignore_paths)


def _operations(document: dict, ignore_paths: list[str]) -> set[str]:
    """`METHOD path` for every operation the spec declares."""
    operations = set()
    for path, item in (document.get("paths") or {}).items():
        if not isinstance(item, dict) or _is_ignored(str(path), ignore_paths):
            continue
        for method in HTTP_METHODS:
            if method in item:
                operations.add(f"{method.upper()} {path}")
    return operations


def _compare_operations(committed: set[str], served: set[str], issues: list[str]) -> dict:
    """Drift between the committed spec and the one the API serves."""
    missing_from_committed = sorted(served - committed)
    missing_from_served = sorted(committed - served)

    for operation in missing_from_committed:
        issues.append(
            f"`{operation}` is served but missing from the committed spec — "
            "the committed artifact is stale"
        )
    for operation in missing_from_served:
        issues.append(
            f"`{operation}` is in the committed spec but the live API doesn't serve it"
        )
    return {
        "missing_from_committed": missing_from_committed,
        "missing_from_served": missing_from_served,
    }


# ── path probing ─────────────────────────────────────────────────


def _parameterless_paths(document: dict, ignore_paths: list[str]) -> tuple[list[str], list[str]]:
    """(probeable, skipped) — a path with `{param}` can't be probed honestly."""
    probeable, skipped = [], []
    for path in (document.get("paths") or {}):
        path = str(path)
        if _is_ignored(path, ignore_paths):
            continue
        (skipped if "{" in path else probeable).append(path)
    return sorted(probeable), sorted(skipped)


def _probe_paths(url: str, paths: list[str], issues: list[str]) -> list[dict]:
    """GET each documented path; 404 and 5xx mean the spec is lying."""
    results = []
    for path in paths:
        target = f"{url.rstrip('/')}{path if path.startswith('/') else '/' + path}"
        status = _probe_status(target)
        ok = status is not None and status != 404 and status < 500
        if status is None:
            issues.append(f"`{path}` is documented but the request never landed")
        elif status == 404:
            issues.append(f"`{path}` is documented but the API returns 404 — the route is gone")
        elif status >= 500:
            issues.append(f"`{path}` is documented but the API returns HTTP {status}")
        results.append({"path": path, "status": status, "ok": ok})
    return results


# ── audit ────────────────────────────────────────────────────────


def _audit_served_spec(served_spec: str, committed: set[str], opts: dict, issues: list[str]) -> dict:
    """Load the served spec and diff its operations against the committed set."""
    text, error = _load_spec_text(served_spec)
    if error:
        issues.append(f"served spec unreadable — {error}")
        return {}
    document, error = _parse_spec(text, "the served spec")
    if error:
        issues.append(error)
        return {}
    served = _operations(document, opts["ignore_paths"])
    return _compare_operations(committed, served, issues)


def _audit(url: str | None, document: dict, opts: dict) -> dict:
    issues: list[str] = []
    notes: list[str] = []

    issues.extend(_validate_shape(document, "the spec"))
    committed = _operations(document, opts["ignore_paths"])
    probeable, skipped = _parameterless_paths(document, opts["ignore_paths"])

    drift = {}
    if opts["served_spec"]:
        drift = _audit_served_spec(opts["served_spec"], committed, opts, issues)
    elif not _spec_is_url(opts["spec"]):
        notes.append(
            "no `api.openapi.served_spec` set — the committed spec isn't being compared "
            "against what the API actually serves, which is the drift most worth catching"
        )

    probes: list[dict] = []
    if opts["probe_paths"] and url and probeable:
        probes = _probe_paths(url, probeable, issues)
    elif opts["probe_paths"] and not url:
        notes.append("no URL supplied — documented paths were not probed for reachability")

    if skipped:
        notes.append(
            f"{len(skipped)} path(s) take parameters and were not probed — a 404 from one "
            "could mean a missing route or merely a missing record, and this check can't "
            "tell those apart"
        )

    return {
        "url": url,
        "status": "fail" if issues else "pass",
        "operation_count": len(committed),
        "drift": drift,
        "probes": probes,
        "skipped_paths": skipped,
        "issues": issues,
        "notes": notes,
    }


# ── markdown report ──────────────────────────────────────────────


def _render_skip(reason: str, guidance: list[str]) -> list[str]:
    lines = [f"**Overall:** ⏭️ SKIPPED — {reason}", ""]
    lines.extend(guidance)
    lines.append("")
    return lines


def _render_findings(label: str, icon: str, findings: list[str]) -> list[str]:
    if not findings:
        return []
    lines = [f"**{label}:**"]
    lines.extend(f"- {icon} {finding}" for finding in findings)
    lines.append("")
    return lines


def _render_probe_table(probes: list[dict]) -> list[str]:
    if not probes:
        return []
    lines = ["<details><summary>Probed paths</summary>", "", "| Path | Status |", "|---|---|"]
    for probe in probes:
        icon = "✅" if probe["ok"] else "❌"
        status = probe["status"] if probe["status"] is not None else "unreachable"
        lines.append(f"| `{probe['path']}` | {icon} {status} |")
    lines.extend(["", "</details>", ""])
    return lines


def _build_markdown_report(result: dict) -> str:
    lines = ["# 📘 OpenAPI Drift Report", ""]
    if result["status"] == "skipped":
        lines.extend(_render_skip(result["skip_reason"], result.get("skip_guidance", [])))
        return "\n".join(lines) + "\n"

    lines.append(f"**Overall:** {'✅ PASS' if result['status'] == 'pass' else '❌ FAIL'}")
    lines.append("")
    lines.append(f"**Operations declared:** {result['operation_count']}")
    lines.append("")
    lines.extend(_render_findings("Issues", "❌", result["issues"]))
    lines.extend(_render_findings("Notes", "⚠️ ", result["notes"]))
    lines.extend(_render_probe_table(result["probes"]))

    lines.append("---")
    lines.append("")
    lines.append("## How to Fix")
    lines.append("")
    lines.append(
        "- **Served but not committed** → regenerate the spec in the repo from the running "
        "app and commit it. If the spec is generated at build time, point `api.openapi.spec` "
        "at the served URL instead so it can't drift at all."
    )
    lines.append(
        "- **Committed but not served** → either the route was removed and the spec wasn't "
        "updated, or the deploy is behind the spec."
    )
    lines.append(
        "- **Documented path 404s** → the spec describes a route that no longer exists. "
        "Use `api.openapi.ignore_paths` for routes that are deliberately undeployed."
    )
    lines.append(
        "- See [docs/hygiene/README.md](../../../docs/hygiene/README.md) for the full contract."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def _write_reports(result: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2) + "\n")
    REPORT_MD.write_text(_build_markdown_report(result))


def _print_result(result: dict) -> None:
    icon = "✅" if result["status"] == "pass" else "❌"
    output._emit(f"  {icon} {result['operation_count']} operation(s) declared")
    for issue in result["issues"]:
        output._emit(f"      - {issue}")
    for note in result["notes"]:
        output._emit(f"      ⚠️  {note}")


# ── CLI entrypoint ───────────────────────────────────────────────


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run hygiene:openapi", add_help=False)
    p.add_argument("url_positional", nargs="?", default=None, help="Base URL of the API")
    p.add_argument("--url", default=None, help="Base URL of the API")
    p.add_argument("--spec", default=None, help="OpenAPI spec: URL or repo-relative JSON file")
    p.add_argument(
        "--served-spec", default=None, help="URL the live API serves its spec at"
    )
    p.add_argument(
        "--no-probe", action="store_true", help="Don't probe documented paths for reachability"
    )
    p.add_argument(
        "--ignore", action="append", default=[], dest="ignore", help="Path glob to skip (repeatable)"
    )
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _resolve_options(parsed: argparse.Namespace) -> dict:
    spec = parsed.spec or config.get("api.openapi.spec")
    return {
        "spec": str(spec).strip() if spec else "",
        "served_spec": parsed.served_spec or config.get("api.openapi.served_spec") or "",
        "probe_paths": not parsed.no_probe and bool(config.get("api.openapi.probe_paths", True)),
        "ignore_paths": list(parsed.ignore or config.get("api.openapi.ignore_paths", []) or []),
    }


def _skip(reason: str, guidance: list[str]) -> int:
    """Graceful skip — an unconfigured check is not a failing check."""
    output.info(reason)
    for line in guidance:
        output._emit(f"   {line}")
    _write_reports(
        {"status": "skipped", "skip_reason": reason, "skip_guidance": guidance, "issues": []}
    )
    output.success("Nothing to audit — skipping (exit 0).")
    return 0


def _fail(message: str) -> int:
    output.error(message)
    _write_reports(
        {
            "url": None,
            "status": "fail",
            "operation_count": 0,
            "drift": {},
            "probes": [],
            "skipped_paths": [],
            "issues": [message],
            "notes": [],
        }
    )
    return 1


def run(args: list[str] | None = None) -> int:
    parsed = _parse_args(args)
    opts = _resolve_options(parsed)

    if not opts["spec"]:
        return _skip(
            "No api.openapi.spec configured in .slopstopper.yml — nothing to compare.",
            ["Set it to your spec's URL or a JSON file in the repo to enable this check."],
        )

    if _looks_like_yaml(opts["spec"]):
        return _skip(
            f"api.openapi.spec points at a YAML spec ({opts['spec']}) — this check reads JSON only.",
            [
                "slopstopper-cli ships no third-party dependencies, so it can't parse YAML.",
                "Point it at the JSON form instead — most frameworks serve /openapi.json —",
                "e.g. api.openapi.spec: https://api.example.com/openapi.json",
            ],
        )

    text, error = _load_spec_text(opts["spec"])
    if error:
        return _fail(error)

    document, error = _parse_spec(text, f"the spec ({opts['spec']})")
    if error:
        return _fail(error)

    url = parsed.url_positional or parsed.url
    output.status("📘", f"OpenAPI drift audit — spec: {opts['spec']}")
    output.separator()

    result = _audit(url, document, opts)
    _write_reports(result)
    _print_result(result)

    output.separator()
    if result["status"] == "pass":
        output.success("The spec matches the API it documents.")
        return 0
    output.error("Drift detected. See .ss/reports/openapi/openapi-report.md for full details.")
    return 1
