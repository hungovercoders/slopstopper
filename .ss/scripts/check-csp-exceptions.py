#!/usr/bin/env python3

"""
CSP-Exceptions Drift Detector

The SlopStopper site ships a strict Content-Security-Policy on every
path (the `/*` rule in `worker/headers.json`). Per-page CSP relaxations
are permitted but must be documented in `docs/security/CSP_EXCEPTIONS.md`.

This script enforces the contract:

- Every non-`/*` entry in `worker/headers.json` whose `Content-Security-Policy`
  adds external origins must have a matching `## /<path>` heading in
  CSP_EXCEPTIONS.md
- Every origin allowed by the CSP entry must be listed under
  `**Origin allowed:**` for that heading
- Every CSP_EXCEPTIONS.md heading must correspond to a real
  `worker/headers.json` entry (catches stale documentation)

Generates a report at .ss/reports/csp/csp-exceptions-report.{md,json}
mirroring the docs-accuracy check.

Exit codes:
  0 — worker/headers.json and CSP_EXCEPTIONS.md agree
  1 — drift detected (details in report)
  2 — required input files missing
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HEADERS_JSON = Path("worker/headers.json")
EXCEPTIONS_DOC = Path("docs/security/CSP_EXCEPTIONS.md")
REPORT_DIR = Path(".ss/reports/csp")

REQUIRED_FIELDS = {
    "Origin allowed",
    "Directives added",
    "Loader SRI",
    "Why",
    "Approved by",
    "Data leaving site",
    "Refresh policy",
}

ORIGIN_RE = re.compile(r"https?://[^\s`'\"\)\],]+")
HEADING_RE = re.compile(r"^###\s+`?(/[^\s`]+)`?\s*$")
FIELD_RE = re.compile(r"^-\s*\*\*([^:*]+):\*\*\s*(.*)$")


# ── worker/headers.json reader ─────────────────────────────────────

def load_headers_json(headers_path: Path) -> list[dict]:
    """Return list of {for: str, csp: str|None} for each entry in worker/headers.json."""
    if not headers_path.exists():
        return []
    raw = json.loads(headers_path.read_text())
    if not isinstance(raw, list):
        return []
    rules: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        path = entry.get("for")
        values = entry.get("values") or {}
        if not isinstance(path, str) or not isinstance(values, dict):
            continue
        csp = values.get("Content-Security-Policy")
        rules.append({"for": path, "csp": csp if isinstance(csp, str) else None})
    return rules


def extract_csp_origins(csp: str) -> set[str]:
    """Return the set of non-self/keyword origins (e.g. https://giscus.app) in a CSP string."""
    origins: set[str] = set()
    for directive in csp.split(";"):
        for token in directive.strip().split():
            if token.startswith(("http://", "https://")):
                origins.add(token.rstrip("/"))
    return origins


# ── CSP_EXCEPTIONS.md parser ────────────────────────────────────────

def _new_entry() -> dict:
    return {"origins": set(), "sri": None, "fields_seen": set()}


def _apply_doc_field(entry: dict, field: str, value: str) -> None:
    """Update a doc entry with one parsed '- **Field:** value' line."""
    entry["fields_seen"].add(field)
    if field in {"Origin allowed", "Directives added"}:
        entry["origins"].update(o.rstrip("/") for o in ORIGIN_RE.findall(value))
    elif field == "Loader SRI":
        entry["sri"] = value.split()[0] if value else None


def _flush_doc_entry(out: dict, state: dict) -> None:
    if state["current"] is not None and state["path"] is not None:
        out[state["path"]] = state["current"]
        state["current"] = None
        state["path"] = None


def _handle_doc_line(out: dict, state: dict, line: str) -> None:
    """Update parser state with one stripped CSP_EXCEPTIONS.md line."""
    if line.startswith("## "):
        _flush_doc_entry(out, state)
        state["in_section"] = line.strip() == "## Exceptions"
        return
    if not state["in_section"]:
        return
    heading = HEADING_RE.match(line)
    if heading:
        _flush_doc_entry(out, state)
        state["path"] = heading.group(1)
        state["current"] = _new_entry()
        return
    if state["current"] is None:
        return
    field = FIELD_RE.match(line)
    if field:
        _apply_doc_field(state["current"], field.group(1).strip(), field.group(2).strip())


def parse_exceptions_doc(doc_path: Path) -> dict[str, dict]:
    """Return {path: {origins: set, sri: str|None, fields_seen: set}} for each ### heading under '## Exceptions'."""
    if not doc_path.exists():
        return {}
    out: dict[str, dict] = {}
    state: dict = {"in_section": False, "path": None, "current": None}
    for raw_line in doc_path.read_text().splitlines():
        _handle_doc_line(out, state, raw_line.rstrip())
    _flush_doc_entry(out, state)
    return out


# ── Comparison ──────────────────────────────────────────────────────

def _headers_exception_map(rules: list[dict]) -> dict[str, set[str]]:
    """Return {path: external_origins} for non-/* CSP entries that admit external origins."""
    out: dict[str, set[str]] = {}
    for rule in rules:
        path = rule["for"]
        if path == "/*" or rule["csp"] is None:
            continue
        external = extract_csp_origins(rule["csp"])
        if external:
            out[path] = external
    return out


def _issues_for_documented_path(path: str, required: set[str], entry: dict) -> list[dict]:
    """All issues for a path that exists in both worker/headers.json and the doc."""
    issues: list[dict] = []
    missing_origins = required - entry["origins"]
    if missing_origins:
        issues.append({
            "severity": "error",
            "path": path,
            "message": f"`{path}` allows {', '.join(sorted(missing_origins))} in worker/headers.json but those origins are not listed in CSP_EXCEPTIONS.md",
        })
    missing_fields = REQUIRED_FIELDS - entry["fields_seen"]
    if missing_fields:
        issues.append({
            "severity": "error",
            "path": path,
            "message": f"`{path}` is missing required field(s) in CSP_EXCEPTIONS.md: {', '.join(sorted(missing_fields))}",
        })
    issues.extend(_sri_issues(path, entry["sri"] or ""))
    return issues


def _sri_issues(path: str, sri: str) -> list[dict]:
    """Warn-only issues about the Loader SRI value."""
    if "TODO" in sri.upper():
        return [{
            "severity": "warn",
            "path": path,
            "message": f"`{path}` Loader SRI is a placeholder ({sri}) — refresh before this exception ships",
        }]
    if not sri:
        return [{
            "severity": "warn",
            "path": path,
            "message": f"`{path}` has no Loader SRI — acceptable if the third party does not support SRI; document why in the entry",
        }]
    return []


def compare(rules: list[dict], doc_entries: dict[str, dict]) -> list[dict]:
    """Return a list of issues (each {severity, path, message})."""
    issues: list[dict] = []
    headers_map = _headers_exception_map(rules)

    # 1) Every headers.json exception must have a matching doc heading covering its origins
    for path, required in headers_map.items():
        entry = doc_entries.get(path)
        if entry is None:
            issues.append({
                "severity": "error",
                "path": path,
                "message": f"`{path}` in worker/headers.json allows external origins ({', '.join(sorted(required))}) but has no entry in CSP_EXCEPTIONS.md",
            })
            continue
        issues.extend(_issues_for_documented_path(path, required, entry))

    # 2) Every doc heading must correspond to a real worker/headers.json entry (catch stale docs)
    for path in doc_entries:
        if path not in headers_map:
            issues.append({
                "severity": "error",
                "path": path,
                "message": f"`{path}` is documented in CSP_EXCEPTIONS.md but no matching CSP exception exists in worker/headers.json",
            })

    return issues


# ── Report writers ─────────────────────────────────────────────────

def _write_json_report(issues: list[dict], summary: dict) -> None:
    (REPORT_DIR / "csp-exceptions-report.json").write_text(
        json.dumps({"summary": summary, "issues": issues}, indent=2) + "\n"
    )


def _overall_status(issues: list[dict]) -> str:
    if any(i["severity"] == "error" for i in issues):
        return "❌ FAIL"
    if any(i["severity"] == "warn" for i in issues):
        return "⚠️ WARN"
    return "✅ PASS"


def _md_issue_section(title: str, severity: str, issues: list[dict]) -> list[str]:
    bucket = [i for i in issues if i["severity"] == severity]
    if not bucket:
        return []
    lines = [title, ""]
    lines.extend(f"- **{i['path']}** — {i['message']}" for i in bucket)
    lines.append("")
    return lines


def _md_fix_section() -> list[str]:
    return [
        "## How to Fix",
        "",
        "- **Missing doc entry** → add a `### \\`/path\\`` heading under `## Exceptions` in `docs/security/CSP_EXCEPTIONS.md` with all required fields.",
        "- **Mismatched origins** → make `Origin allowed` / `Directives added` in the doc list every external origin in the corresponding `worker/headers.json` entry.",
        "- **Stale doc entry** → remove the heading, or restore the matching entry in `worker/headers.json`.",
        "- **Placeholder SRI** → recompute with the procedure documented in `CSP_EXCEPTIONS.md` and update both the doc and `app/feedback.html`.",
        "",
    ]


def _write_markdown_report(issues: list[dict], summary: dict) -> None:
    lines: list[str] = [
        "# 🔐 CSP Exceptions Report",
        "",
        f"**Status:** {_overall_status(issues)}",
        "",
        f"- Documented exceptions in `docs/security/CSP_EXCEPTIONS.md`: {summary['doc_entries']}",
        f"- CSP exceptions in `worker/headers.json` (non-`/*`): {summary['headers_exceptions']}",
        "",
    ]
    if not issues:
        lines.extend(["No drift detected. `worker/headers.json` and `CSP_EXCEPTIONS.md` agree.", ""])
    else:
        lines.extend(_md_issue_section("## ❌ Errors", "error", issues))
        lines.extend(_md_issue_section("## ⚠️ Warnings", "warn", issues))
    lines.extend(_md_fix_section())
    (REPORT_DIR / "csp-exceptions-report.md").write_text("\n".join(lines) + "\n")


def write_reports(issues: list[dict], summary: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_report(issues, summary)
    _write_markdown_report(issues, summary)


# ── Main ───────────────────────────────────────────────────────────

def _print_results(headers_count: int, doc_count: int, issues: list[dict]) -> None:
    print("🔐 CSP exceptions check")
    print(f"   worker/headers.json CSP exceptions: {headers_count}")
    print(f"   documented in CSP_EXCEPTIONS.md: {doc_count}")
    print("━" * 60)
    if not issues:
        print("✅ No drift detected.")
        return
    for i in issues:
        icon = "❌" if i["severity"] == "error" else "⚠️ "
        print(f"   {icon} {i['path']}: {i['message']}")
    print("━" * 60)


def main() -> int:
    if not HEADERS_JSON.exists():
        print("❌ worker/headers.json not found", file=sys.stderr)
        return 2
    if not EXCEPTIONS_DOC.exists():
        print("❌ docs/security/CSP_EXCEPTIONS.md not found", file=sys.stderr)
        return 2

    rules = load_headers_json(HEADERS_JSON)
    doc_entries = parse_exceptions_doc(EXCEPTIONS_DOC)
    headers_count = len(_headers_exception_map(rules))
    issues = compare(rules, doc_entries)

    write_reports(issues, {"doc_entries": len(doc_entries), "headers_exceptions": headers_count})
    _print_results(headers_count, len(doc_entries), issues)

    if any(i["severity"] == "error" for i in issues):
        print("❌ Drift detected. See .ss/reports/csp/csp-exceptions-report.md for full details.")
        return 1
    if issues:
        print("⚠️  Warnings only — passing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
