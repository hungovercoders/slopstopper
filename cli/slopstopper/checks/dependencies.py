"""Dependency vulnerability scanning (Trivy wrapper).

Ports the bash security:vulnerability:all flow:

  task vulnerability:all:check-tool   (installs trivy if missing)
  + trivy fs --format json --output=... --skip-dirs node_modules
             --skip-dirs .git .
  + python3 .ss/scripts/generate-dependencies-md.py

into one self-contained check. Subprocess-invokes trivy — same
licensing-boundary pattern as gitleaks (MIT) and semgrep (LGPL-2.1):
adopters install the binary themselves, the CLI wheel ships zero
trivy code. Trivy itself is Apache-2.0 so the boundary is gentler
than semgrep's, but the discipline is identical.

Exit codes:
  0 — analysis completed (gating happens at the workflow level)
  1 — trivy is not installed
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path(".ss/reports/dependencies")
REPORT_JSON = REPORT_DIR / "dependencies-report.json"
REPORT_MD = REPORT_DIR / "dependencies-report.md"

_INSTALL_HELP = (
    "❌ trivy is not installed.\n"
    "Install with:\n"
    "  brew install aquasecurity/trivy/trivy     # macOS\n"
    "  sudo apt-get install trivy                # Debian/Ubuntu (with trivy apt repo)\n"
    "More: https://trivy.dev/latest/getting-started/installation/"
)


def _trivy_available() -> bool:
    return shutil.which("trivy") is not None


def _run_trivy() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "trivy", "fs",
            "--format", "json",
            "--output", str(REPORT_JSON),
            "--skip-dirs", "node_modules",
            "--skip-dirs", ".git",
            ".",
        ],
        check=False,
    )


def _read_data() -> dict:
    if not REPORT_JSON.exists():
        return {}
    try:
        return json.loads(REPORT_JSON.read_text())
    except json.JSONDecodeError:
        return {}


def _collect_vulnerabilities(data: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    critical: list[dict] = []
    high: list[dict] = []
    medium: list[dict] = []
    low: list[dict] = []
    for result in data.get("Results", []):
        target = result.get("Target", "unknown")
        for vuln in result.get("Vulnerabilities", []):
            entry = {
                "id": vuln.get("VulnerabilityID", "unknown"),
                "pkg": vuln.get("PkgName", "unknown"),
                "installed": vuln.get("InstalledVersion", "?"),
                "fixed": vuln.get("FixedVersion", "none"),
                "severity": vuln.get("Severity", "UNKNOWN"),
                "title": vuln.get("Title", ""),
                "target": target,
            }
            sev = entry["severity"].upper()
            if sev == "CRITICAL":
                critical.append(entry)
            elif sev == "HIGH":
                high.append(entry)
            elif sev == "MEDIUM":
                medium.append(entry)
            else:
                low.append(entry)
    return critical, high, medium, low


def _format_vuln_row(v: dict) -> str:
    title = (v["title"][:57] + "...") if len(v["title"]) > 60 else v["title"]
    return (
        f"| {v['id']} | `{v['pkg']}` | {v['installed']} | {v['fixed']} "
        f"| {v['severity']} | {title} |"
    )


def _format_vuln_section(vulns: list[dict], section_title: str, icon: str) -> str:
    if not vulns:
        return ""
    out = f"## {icon} {section_title}\n\n"
    out += "| CVE | Package | Installed | Fixed In | Severity | Title |\n"
    out += "|-----|---------|-----------|----------|----------|-------|\n"
    for v in vulns:
        out += _format_vuln_row(v) + "\n"
    out += "\n"
    return out


def _generated_at() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _build_md_report(data: dict) -> str:
    critical, high, medium, low = _collect_vulnerabilities(data)
    total = len(critical) + len(high) + len(medium) + len(low)

    md = "# Dependency Vulnerability Report\n\n"
    md += f"**Generated**: {_generated_at()}\n\n"
    md += "## Summary\n\n"

    if total == 0:
        md += "## ✅ Dependencies Status\n\nNo vulnerabilities detected.\n\n"
    else:
        md += "| Severity | Count |\n"
        md += "|----------|-------|\n"
        md += f"| 🔴 Critical | {len(critical)} |\n"
        md += f"| 🟠 High | {len(high)} |\n"
        md += f"| 🟡 Medium | {len(medium)} |\n"
        md += f"| 🔵 Low | {len(low)} |\n"
        md += f"| **Total** | **{total}** |\n\n"
        md += _format_vuln_section(critical, "Critical Vulnerabilities", "🔴")
        md += _format_vuln_section(high, "High Vulnerabilities", "🟠")
        md += _format_vuln_section(medium, "Medium Vulnerabilities", "🟡")
        md += _format_vuln_section(low, "Low Vulnerabilities", "🔵")

    md += "## Guidelines\n\n"
    md += "- **Critical/High**: Update or replace the vulnerable package before merging\n"
    md += "- **Medium**: Review and plan remediation\n"
    md += "- **Low**: Informational — update when convenient\n"
    md += "- Run `task dependencies` locally to reproduce\n\n"
    md += "## More Information\n\n"
    md += "- Generated by [Trivy](https://trivy.dev/)\n"
    md += "- Reports location: `.ss/reports/dependencies/`\n"
    md += "  - `dependencies-report.md` (this file)\n"
    md += "  - `dependencies-report.json` (machine-readable)\n"
    return md


def run(_args: list[str] | None = None) -> int:
    if not _trivy_available():
        print(_INSTALL_HELP)
        return 1

    print("🔍 Scanning dependencies for vulnerabilities…")
    _run_trivy()
    data = _read_data()
    REPORT_MD.write_text(_build_md_report(data))

    critical, high, medium, low = _collect_vulnerabilities(data)
    total = len(critical) + len(high) + len(medium) + len(low)
    blocking = len(critical) + len(high)
    if blocking > 0:
        print(f"⚠️  Found {blocking} CRITICAL/HIGH vulnerability(ies) (total {total})")
    elif total > 0:
        print(f"ℹ️  Found {total} vulnerability(ies) — none CRITICAL/HIGH")
    else:
        print("✅ No vulnerabilities detected")
    print(f"📁 Reports saved to: {REPORT_DIR}/")
    return 0
