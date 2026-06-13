"""DAST blocking-alerts gate (lifted from .ss/scripts/check-dast-alerts.py).

Decides which ZAP findings should fail the build, with one narrow
exception: CSP findings on paths that are explicitly documented in
`docs/security/CSP_EXCEPTIONS.md`.

Why this filter exists:
The site ships a strict CSP on `/*`. Where a vetted third-party
widget genuinely requires a relaxation (e.g. Giscus on
`/feedback.html`) we admit it via a per-path `[[headers]]` block AND
document it in `CSP_EXCEPTIONS.md`. ZAP correctly flags the relaxed
CSP as a Medium finding. Because that relaxation was reviewed and
approved, this gate swallows that *specific* class of finding on
that *specific* path without quieting any other class of issue.

What still blocks (intentional):
- Any alert with riskcode >= 2 on a path NOT in CSP_EXCEPTIONS.md
- Any non-CSP alert on a documented exception path (XSS, missing
  other headers, CSRF, etc.)
- High (riskcode 3) alerts everywhere, even CSP ones on exception
  paths — `Refresh policy` and approval still don't make a high-risk
  finding acceptable.

Outputs:
- `.ss/reports/dast/dast-gate.json` with {blocking, swallowed[]}
- The `swallowed_preamble_md()` helper renders the same
  "🛡 Documented CSP exceptions" block the legacy JS used to
  prepend to the PR comment, so emit-routed PR comments keep
  showing which findings were filtered out.
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ZAP_REPORT = Path(".ss/reports/dast/dast-report.json")
EXCEPTIONS_DOC = Path("docs/security/CSP_EXCEPTIONS.md")
ZAP_RULES_FILE = Path(".zap/rules.tsv")
GATE_REPORT = Path(".ss/reports/dast/dast-gate.json")

# ZAP plugin IDs that report on Content Security Policy issues.
# See https://www.zaproxy.org/docs/alerts/ for the full registry.
CSP_PLUGIN_IDS = {"10038", "10055", "10056", "10063"}
CSP_NAME_HINTS = ("content security policy", "csp")

HEADING_RE = re.compile(r"###\s+`?(/[^\s`]+)`?")


# ── Documented-path parser ──────────────────────────────────────────


def documented_exception_paths(doc: Path = EXCEPTIONS_DOC) -> set[str]:
    """Return the set of paths that have an entry under '## Exceptions'."""
    if not doc.exists():
        return set()
    paths: set[str] = set()
    in_section = False
    for raw in doc.read_text().splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_section = line == "## Exceptions"
            continue
        if in_section and line.startswith("### "):
            m = HEADING_RE.match(line)
            if m:
                paths.add(m.group(1))
    return paths


def ignored_plugin_ids(rules_file: Path = ZAP_RULES_FILE) -> set[str]:
    """Return the set of ZAP plugin IDs the consumer has marked IGNORE in .zap/rules.tsv.

    ZAP's `-c` flag stops these rules from FAILing the scan but still
    leaves the findings in the JSON report with their original
    riskcode. The gate honours the same allowlist so a `90003 IGNORE`
    (e.g. SRI on a rotating cross-domain script) doesn't keep
    blocking the build just because ZAP recorded the alert anyway.
    """
    if not rules_file.exists():
        return set()
    ignored: set[str] = set()
    for raw in rules_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].strip().upper() == "IGNORE":
            ignored.add(parts[0].strip())
    return ignored


# ── Alert classification ────────────────────────────────────────────


def is_csp_alert(alert: dict) -> bool:
    pid = str(alert.get("pluginid", ""))
    if pid in CSP_PLUGIN_IDS:
        return True
    name = (alert.get("alert", "") + " " + alert.get("name", "")).lower()
    return any(h in name for h in CSP_NAME_HINTS)


def instance_path(uri: str) -> str:
    return urlparse(uri).path or "/"


def riskcode(alert: dict) -> int:
    try:
        return int(alert.get("riskcode", 0))
    except (TypeError, ValueError):
        return 0


def _match_exception_path(path: str, exception_paths: set[str]) -> str | None:
    """Return the matching exception-path pattern for `path`, or None.

    Documented paths support shell-style globs so site-wide
    relaxations (`/*`) and section-wide relaxations (`/blog/*`) can
    be expressed without listing every actual URL. Literal paths
    still match exactly. Returns the pattern that matched so the
    swallow record carries provenance back to the doc, not the
    resolved URL path.
    """
    for pattern in exception_paths:
        if path == pattern or fnmatch.fnmatch(path, pattern):
            return pattern
    return None


def _classify_instance(alert: dict, uri: str, exception_paths: set[str]) -> dict | None:
    """Return a swallow-record if this instance is a documented CSP exception, else None."""
    if riskcode(alert) >= 3:
        return None  # High-risk CSP findings still block, even on exception paths
    if not is_csp_alert(alert):
        return None
    path = instance_path(uri)
    matched = _match_exception_path(path, exception_paths)
    if matched is None:
        return None
    return {
        "path": matched,
        "uri": uri,
        "pluginid": str(alert.get("pluginid", "")),
        "alert": alert.get("alert") or alert.get("name", ""),
        "riskcode": riskcode(alert),
    }


def classify_alerts(
    zap_data: dict,
    exception_paths: set[str],
    ignored_pluginids: set[str],
) -> tuple[int, list[dict]]:
    """Return (blocking_count, swallowed_records) across all sites/alerts/instances."""
    blocking = 0
    swallowed: list[dict] = []
    for site in zap_data.get("site", []):
        for alert in site.get("alerts", []):
            if riskcode(alert) < 2:
                continue
            pid = str(alert.get("pluginid", ""))
            instances = alert.get("instances") or [{"uri": alert.get("url", "")}]
            for inst in instances:
                # Rule-level IGNORE in .zap/rules.tsv: swallow
                # regardless of path or alert class — the consumer has
                # explicitly accepted this finding type for the whole
                # site.
                if pid in ignored_pluginids:
                    swallowed.append({
                        "path": instance_path(inst.get("uri", "")),
                        "uri": inst.get("uri", ""),
                        "pluginid": pid,
                        "alert": alert.get("alert") or alert.get("name", ""),
                        "riskcode": riskcode(alert),
                        "source": ".zap/rules.tsv",
                    })
                    continue
                record = _classify_instance(alert, inst.get("uri", ""), exception_paths)
                if record is not None:
                    record["source"] = "docs/security/CSP_EXCEPTIONS.md"
                    swallowed.append(record)
                else:
                    blocking += 1
    return blocking, swallowed


def compute_gate(zap_data: dict) -> tuple[int, list[dict]]:
    """Run the full gate using the docs/rules sources on disk."""
    exception_paths = documented_exception_paths()
    ignored = ignored_plugin_ids()
    return classify_alerts(zap_data, exception_paths, ignored)


# ── Reporting ──────────────────────────────────────────────────────


def write_gate_report(blocking: int, swallowed: list[dict]) -> None:
    GATE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    GATE_REPORT.write_text(json.dumps({
        "blocking": blocking,
        "swallowed": swallowed,
    }, indent=2) + "\n")


def swallowed_preamble_md(swallowed: list[dict]) -> str:
    """Render the "🛡 Documented CSP exceptions" preamble block.

    Same shape as the pre-flip JS produced. Empty string when no
    findings were swallowed — keeps the report MD clean on the happy
    path.
    """
    if not swallowed:
        return ""
    lines = [
        "### 🛡 Documented CSP exceptions (swallowed by gate)",
        "",
        f"{len(swallowed)} CSP finding(s) on documented exception paths were filtered out:",
        "",
    ]
    for s in swallowed:
        lines.append(
            f"- **{s['path']}** — pluginid `{s['pluginid']}`, "
            f"riskcode {s['riskcode']}, _{s['alert']}_"
        )
    lines += [
        "",
        "These do not block the build. They will block again if the path "
        "is removed from the exceptions doc or if a higher-risk variant appears.",
        "",
    ]
    return "\n".join(lines) + "\n"


def format_summary_text(blocking: int, swallowed: list[dict]) -> str:
    out = [
        "🕷️  DAST gate",
        f"   blocking alerts (riskcode >= 2): {blocking}",
        f"   swallowed (documented CSP exceptions): {len(swallowed)}",
        "━" * 60,
    ]
    for s in swallowed:
        out.append(
            f"   🛡 {s['path']}: pluginid={s['pluginid']} riskcode={s['riskcode']} {s['alert']!r}"
        )
    if swallowed:
        out.append("━" * 60)
    if blocking == 0:
        out.append("✅ No blocking findings.")
    else:
        out.append(
            f"❌ {blocking} blocking finding(s). See .ss/reports/dast/dast-report.md."
        )
    return "\n".join(out)
