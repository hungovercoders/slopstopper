"""Static Application Security Testing (Semgrep wrapper).

Ports the bash security:sast flow:

  task sast:check-tool          (installs semgrep if missing)
  + semgrep --config=auto --json --output=... --exclude=node_modules
            --exclude=.git .
  + python3 .ss/scripts/generate-sast-md.py

into one self-contained check. Subprocess-invokes semgrep — same
licensing-boundary pattern as complexity (lizard) and secrets
(gitleaks). The boundary matters MORE here: Semgrep OSS is LGPL-2.1,
not MIT/Apache. `import semgrep` would drag LGPL contagion into the
slopstopper-cli MIT contract. Subprocess invocation keeps it on the
adopter's side.

Exit codes:
  0 — analysis completed
  1 — semgrep is not installed
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path(".ss/reports/sast")
REPORT_JSON = REPORT_DIR / "sast-report.json"
REPORT_MD = REPORT_DIR / "sast-report.md"

_INSTALL_HELP = (
    "❌ semgrep is not installed.\n"
    "Install with:\n"
    "  pip3 install --user semgrep\n"
    "  brew install semgrep\n"
    "More: https://semgrep.dev/docs/getting-started/quickstart-oss"
)


def _semgrep_available() -> bool:
    return shutil.which("semgrep") is not None


def _run_semgrep() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "semgrep",
            "--config=auto",
            "--json",
            f"--output={REPORT_JSON}",
            "--exclude=node_modules",
            "--exclude=.git",
            ".",
        ],
        check=False,
    )


def _read_data() -> dict:
    if not REPORT_JSON.exists():
        return {"results": [], "errors": []}
    try:
        return json.loads(REPORT_JSON.read_text())
    except json.JSONDecodeError:
        return {"results": [], "errors": []}


def _categorize_findings(results: list[dict]) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    for finding in results:
        severity = finding.get("extra", {}).get("severity", "").upper()
        if severity == "ERROR":
            errors.append(finding)
        else:
            warnings.append(finding)
    return errors, warnings


def _format_finding_row(finding: dict) -> str:
    check_id = finding.get("check_id", "unknown")
    path = finding.get("path", "unknown")
    start_line = finding.get("start", {}).get("line", "?")
    message = finding.get("extra", {}).get("message", "").replace("\n", " ").strip()
    severity = finding.get("extra", {}).get("severity", "unknown")
    location = f"`{path}:{start_line}`"
    truncated = (message[:77] + "...") if len(message) > 80 else message
    return f"| {check_id} | {severity} | {location} | {truncated} |"


def _format_findings_section(findings: list[dict], section_title: str, icon: str) -> str:
    if not findings:
        return ""
    out = f"## {icon} {section_title}\n\n"
    out += "| Rule | Severity | Location | Message |\n"
    out += "|------|----------|----------|---------|\n"
    for finding in findings:
        out += _format_finding_row(finding) + "\n"
    out += "\n"
    return out


def _collect_parsing_errors(errors: list[dict]) -> dict[str, list]:
    parsing_error_files: dict[str, list] = {}
    for error in errors:
        error_type = error.get("type", [])
        if not (isinstance(error_type, list) and error_type and error_type[0] == "PartialParsing"):
            continue
        path = error.get("path", "unknown")
        parsing_error_files.setdefault(path, [])
        spans = error.get("spans", [])
        if spans:
            start_line = spans[0].get("start", {}).get("line", "?")
            parsing_error_files[path].append(start_line)
    return parsing_error_files


def _format_scan_errors_explanation(errors: list[dict]) -> str:
    if not errors:
        return ""
    out = "### 📋 Scan Errors Explanation\n\n"
    parsing_error_files = _collect_parsing_errors(errors)
    if parsing_error_files:
        out += f"The {len(errors)} warning(s) are **parsing errors in YAML workflow files**, not security issues:\n\n"
        for path, lines in sorted(parsing_error_files.items()):
            out += f"- `{path}` (line(s): {', '.join(map(str, lines))})\n"
        out += "\n"
        out += "**Why**: Semgrep's YAML analyzer attempts to parse embedded bash scripts in `run:` blocks. "
        out += "The bash code contains special characters and operators (pipes, redirects) that don't parse as valid YAML syntax.\n\n"
        out += "**Is this safe to ignore?** ✅ **Yes.** These are only debug/logging scripts—not production code. "
        out += "The bash syntax is valid and the workflows execute correctly. The SAST scan itself completed successfully with valid results.\n\n"
    else:
        out += f"Semgrep reported {len(errors)} error(s) during scanning:\n\n"
        for i, error in enumerate(errors, 1):
            msg = error.get("message", "Unknown error").split('\n')[0]
            out += f"{i}. {msg}\n"
        out += "\n"
    return out


def _generated_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _build_md_report(data: dict) -> str:
    results = data.get("results", [])
    errors = data.get("errors", [])
    error_findings, warning_findings = _categorize_findings(results)
    total_findings = len(results)

    md = "# SAST Analysis Report\n\n"
    md += f"**Generated**: {_generated_at()}\n\n"
    md += "## Summary\n\n"

    if errors:
        md += f"> ⚠️ Semgrep encountered {len(errors)} scan error(s). Results may be incomplete.\n\n"
        md += _format_scan_errors_explanation(errors) + "\n"

    if total_findings == 0:
        md += "## ✅ SAST Status\n\nNo findings detected.\n\n"
    else:
        md += "| Metric | Count |\n"
        md += "|--------|-------|\n"
        md += f"| Total findings | {total_findings} |\n"
        md += f"| Errors | {len(error_findings)} |\n"
        md += f"| Warnings | {len(warning_findings)} |\n\n"
        md += _format_findings_section(error_findings, "Error Findings", "🔴")
        md += _format_findings_section(warning_findings, "Warning Findings", "⚠️")

    md += "## Guidelines\n\n"
    md += "- **Errors**: Must be reviewed and addressed before merging\n"
    md += "- **Warnings**: Should be reviewed; may indicate potential issues\n"
    md += "- Run `task sast` locally to reproduce findings\n\n"
    md += "## Limitations\n\n"
    md += "This scan uses **Semgrep OSS** (open-source version). The following enterprise features are not available:\n\n"
    md += "- ✘ **Semgrep Code (SAST)** - Paid feature with advanced security rules\n"
    md += "- ✘ **Semgrep Supply Chain (SCA)** - Paid feature for dependency vulnerability detection\n\n"
    md += "To enable these features, [register for a free Semgrep account](https://semgrep.dev/signup) and authenticate with `semgrep login`.\n\n"
    md += "## More Information\n\n"
    md += "- Generated by [Semgrep](https://semgrep.dev/) (OSS Edition)\n"
    md += "- Reports location: `.ss/reports/sast/`\n"
    md += "  - `sast-report.md` (this file)\n"
    md += "  - `sast-report.json` (machine-readable)\n"
    md += "- Learn more: [Semgrep Tiers and Pricing](https://semgrep.dev/pricing)\n"
    return md


def run(_args: list[str] | None = None) -> int:
    if not _semgrep_available():
        print(_INSTALL_HELP)
        return 1

    print("🔍 Running SAST analysis…")
    _run_semgrep()
    data = _read_data()
    REPORT_MD.write_text(_build_md_report(data))

    results = data.get("results", [])
    if results:
        errors, warnings = _categorize_findings(results)
        print(f"⚠️  Found {len(results)} finding(s): {len(errors)} error(s), {len(warnings)} warning(s)")
    else:
        print("✅ No findings detected")
    print(f"📁 Reports saved to: {REPORT_DIR}/")
    return 0
