#!/usr/bin/env python3

"""
CSP-Exceptions Drift Detector

The SlopStopper site ships a strict Content-Security-Policy on every
path (`for = "/*"` in `netlify.toml`). Per-page CSP relaxations are
permitted but must be documented in `docs/security/CSP_EXCEPTIONS.md`.

This script enforces the contract:

- Every non-`/*` `[[headers]]` block in netlify.toml that adds external
  origins to its CSP must have a matching `## /<path>` heading in
  CSP_EXCEPTIONS.md
- Every origin allowed by the CSP block must be listed under
  `**Origin allowed:**` for that heading
- Every CSP_EXCEPTIONS.md heading must correspond to a real
  netlify.toml block (catches stale documentation)

Generates a report at .ss/reports/csp/csp-exceptions-report.{md,json}
mirroring the docs-accuracy check.

Exit codes:
  0 — netlify.toml and CSP_EXCEPTIONS.md agree
  1 — drift detected (details in report)
  2 — required input files missing
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NETLIFY_TOML = Path("netlify.toml")
EXCEPTIONS_DOC = Path("docs/security/CSP_EXCEPTIONS.md")
REPORT_DIR = Path(".ss/reports/csp")


# ── netlify.toml parser (minimal — matches what server.js parses) ──

def parse_netlify_headers(toml_path: Path) -> list[dict]:
    """Return list of {for: str, csp: str|None} for each [[headers]] block."""
    if not toml_path.exists():
        return []
    rules: list[dict] = []
    current: dict | None = None
    in_values = False
    for raw_line in toml_path.read_text().splitlines():
        line = raw_line.strip()
        if line == "[[headers]]":
            if current is not None:
                rules.append(current)
            current = {"for": None, "csp": None}
            in_values = False
            continue
        if line == "[headers.values]":
            in_values = True
            continue
        if line.startswith("[") and line not in {"[[headers]]", "[headers.values]"}:
            if current is not None:
                rules.append(current)
                current = None
            in_values = False
            continue
        m = re.match(r'^([^=]+?)\s*=\s*"((?:[^"\\]|\\.)*)"$', line)
        if not m or current is None:
            continue
        key, value = m.group(1).strip(), m.group(2)
        if in_values:
            if key == "Content-Security-Policy":
                current["csp"] = value
        elif key == "for":
            current["for"] = value
    if current is not None:
        rules.append(current)
    return [r for r in rules if r["for"] is not None]


def extract_csp_origins(csp: str) -> set[str]:
    """Return the set of non-self/keyword origins (e.g. https://giscus.app) in a CSP string."""
    origins: set[str] = set()
    for directive in csp.split(";"):
        for token in directive.strip().split():
            if token.startswith(("http://", "https://")):
                origins.add(token.rstrip("/"))
    return origins


# ── CSP_EXCEPTIONS.md parser ────────────────────────────────────────

ORIGIN_RE = re.compile(r"https?://[^\s`'\"\)\],]+")
HEADING_RE = re.compile(r"^###\s+`?(/[^\s`]+)`?\s*$")
FIELD_RE = re.compile(r"^-\s*\*\*([^:*]+):\*\*\s*(.*)$")


def parse_exceptions_doc(doc_path: Path) -> dict[str, dict]:
    """Return {path: {origins: set, sri: str|None, fields_seen: set}} for each ### heading under '## Exceptions'."""
    if not doc_path.exists():
        return {}
    exceptions: dict[str, dict] = {}
    current_path: str | None = None
    current: dict | None = None
    in_exceptions_section = False
    for raw_line in doc_path.read_text().splitlines():
        line = raw_line.rstrip()
        if line.strip() == "## Exceptions":
            in_exceptions_section = True
            continue
        if line.startswith("## ") and line.strip() != "## Exceptions":
            in_exceptions_section = False
            if current is not None and current_path is not None:
                exceptions[current_path] = current
                current = None
                current_path = None
            continue
        if not in_exceptions_section:
            continue
        m = HEADING_RE.match(line)
        if m:
            if current is not None and current_path is not None:
                exceptions[current_path] = current
            current_path = m.group(1)
            current = {"origins": set(), "sri": None, "fields_seen": set()}
            continue
        if current is None:
            continue
        fm = FIELD_RE.match(line)
        if fm:
            field, value = fm.group(1).strip(), fm.group(2).strip()
            current["fields_seen"].add(field)
            if field == "Origin allowed":
                current["origins"].update(o.rstrip("/") for o in ORIGIN_RE.findall(value))
            elif field == "Directives added":
                current["origins"].update(o.rstrip("/") for o in ORIGIN_RE.findall(value))
            elif field == "Loader SRI":
                current["sri"] = value.split()[0] if value else None
    if current is not None and current_path is not None:
        exceptions[current_path] = current
    return exceptions


# ── Comparison ──────────────────────────────────────────────────────

REQUIRED_FIELDS = {
    "Origin allowed",
    "Directives added",
    "Loader SRI",
    "Why",
    "Approved by",
    "Data leaving site",
    "Refresh policy",
}


def compare(rules: list[dict], doc_entries: dict[str, dict]) -> list[dict]:
    """Return a list of issues (each {severity, path, message})."""
    issues: list[dict] = []

    # Build a map: path -> set of external origins required by netlify.toml
    toml_map: dict[str, set[str]] = {}
    for rule in rules:
        path = rule["for"]
        if path == "/*" or rule["csp"] is None:
            continue
        external = extract_csp_origins(rule["csp"])
        if external:
            toml_map[path] = external

    # 1) Every toml exception must have a matching doc heading covering its origins
    for path, required_origins in toml_map.items():
        entry = doc_entries.get(path)
        if entry is None:
            issues.append({
                "severity": "error",
                "path": path,
                "message": f"`{path}` in netlify.toml allows external origins ({', '.join(sorted(required_origins))}) but has no entry in CSP_EXCEPTIONS.md",
            })
            continue
        documented = entry["origins"]
        missing = required_origins - documented
        if missing:
            issues.append({
                "severity": "error",
                "path": path,
                "message": f"`{path}` allows {', '.join(sorted(missing))} in netlify.toml but those origins are not listed in CSP_EXCEPTIONS.md",
            })
        # Required fields present?
        missing_fields = REQUIRED_FIELDS - entry["fields_seen"]
        if missing_fields:
            issues.append({
                "severity": "error",
                "path": path,
                "message": f"`{path}` is missing required field(s) in CSP_EXCEPTIONS.md: {', '.join(sorted(missing_fields))}",
            })
        # SRI placeholder check (warn — TODO is acceptable in a draft PR but flagged)
        sri = entry["sri"] or ""
        if "TODO" in sri.upper():
            issues.append({
                "severity": "warn",
                "path": path,
                "message": f"`{path}` Loader SRI is a placeholder ({sri}) — refresh before this exception ships",
            })
        elif not sri:
            issues.append({
                "severity": "warn",
                "path": path,
                "message": f"`{path}` has no Loader SRI — acceptable if the third party does not support SRI; document why in the entry",
            })

    # 2) Every doc heading must correspond to a real netlify.toml block (catch stale docs)
    for path in doc_entries:
        if path not in toml_map:
            issues.append({
                "severity": "error",
                "path": path,
                "message": f"`{path}` is documented in CSP_EXCEPTIONS.md but no matching CSP exception exists in netlify.toml",
            })

    return issues


# ── Report writers ─────────────────────────────────────────────────

def write_reports(issues: list[dict], summary: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPORT_DIR / "csp-exceptions-report.json"
    json_path.write_text(json.dumps({
        "summary": summary,
        "issues": issues,
    }, indent=2) + "\n")

    md_path = REPORT_DIR / "csp-exceptions-report.md"
    lines: list[str] = []
    lines.append("# 🔐 CSP Exceptions Report")
    lines.append("")
    errors = [i for i in issues if i["severity"] == "error"]
    warns = [i for i in issues if i["severity"] == "warn"]
    overall = "❌ FAIL" if errors else ("⚠️ WARN" if warns else "✅ PASS")
    lines.append(f"**Status:** {overall}")
    lines.append("")
    lines.append(f"- Documented exceptions in `docs/security/CSP_EXCEPTIONS.md`: {summary['doc_entries']}")
    lines.append(f"- CSP exceptions in `netlify.toml` (non-`/*`): {summary['toml_exceptions']}")
    lines.append("")
    if not issues:
        lines.append("No drift detected. `netlify.toml` and `CSP_EXCEPTIONS.md` agree.")
        lines.append("")
    else:
        if errors:
            lines.append("## ❌ Errors")
            lines.append("")
            for i in errors:
                lines.append(f"- **{i['path']}** — {i['message']}")
            lines.append("")
        if warns:
            lines.append("## ⚠️ Warnings")
            lines.append("")
            for i in warns:
                lines.append(f"- **{i['path']}** — {i['message']}")
            lines.append("")
    lines.append("## How to Fix")
    lines.append("")
    lines.append("- **Missing doc entry** → add a `### \\`/path\\`` heading under `## Exceptions` in `docs/security/CSP_EXCEPTIONS.md` with all required fields.")
    lines.append("- **Mismatched origins** → make `Origin allowed` / `Directives added` in the doc list every external origin in the corresponding `netlify.toml` CSP.")
    lines.append("- **Stale doc entry** → remove the heading, or restore the matching `[[headers]]` block in `netlify.toml`.")
    lines.append("- **Placeholder SRI** → recompute with the procedure documented in `CSP_EXCEPTIONS.md` and update both the doc and `app/feedback.html`.")
    lines.append("")
    md_path.write_text("\n".join(lines) + "\n")


# ── Main ───────────────────────────────────────────────────────────

def main() -> int:
    if not NETLIFY_TOML.exists():
        print("❌ netlify.toml not found", file=sys.stderr)
        return 2
    if not EXCEPTIONS_DOC.exists():
        print("❌ docs/security/CSP_EXCEPTIONS.md not found", file=sys.stderr)
        return 2

    rules = parse_netlify_headers(NETLIFY_TOML)
    doc_entries = parse_exceptions_doc(EXCEPTIONS_DOC)

    toml_exceptions = sum(1 for r in rules if r["for"] != "/*" and r["csp"] and extract_csp_origins(r["csp"]))

    issues = compare(rules, doc_entries)
    summary = {
        "doc_entries": len(doc_entries),
        "toml_exceptions": toml_exceptions,
    }
    write_reports(issues, summary)

    errors = [i for i in issues if i["severity"] == "error"]
    warns = [i for i in issues if i["severity"] == "warn"]

    print("🔐 CSP exceptions check")
    print(f"   netlify.toml CSP exceptions: {toml_exceptions}")
    print(f"   documented in CSP_EXCEPTIONS.md: {len(doc_entries)}")
    print("━" * 60)
    if not issues:
        print("✅ No drift detected.")
        return 0
    for i in errors:
        print(f"   ❌ {i['path']}: {i['message']}")
    for i in warns:
        print(f"   ⚠️  {i['path']}: {i['message']}")
    print("━" * 60)
    if errors:
        print("❌ Drift detected. See .ss/reports/csp/csp-exceptions-report.md for full details.")
        return 1
    print("⚠️  Warnings only — passing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
