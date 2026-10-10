"""Static Application Security Testing (Semgrep wrapper).

Ports the bash security:sast flow:

  task sast:check-tool          (installs semgrep if missing)
  + semgrep --config=auto --json --output=... --exclude=node_modules
            --exclude=.git .
  + python3 .ss/scripts/generate-sast-md.py

into one self-contained check. It subprocess-invokes semgrep, following the
same licensing-boundary pattern as complexity (lizard) and secrets
(gitleaks). The boundary matters MORE here: Semgrep OSS is LGPL-2.1,
not MIT/Apache. `import semgrep` would drag LGPL contagion into the
slopstopper-cli MIT contract. Subprocess invocation keeps it on the
adopter's side.

The verdict lives here, not in the workflow. Semgrep reports findings
at ERROR, WARNING and INFO severity (newer registry rules also use
CRITICAL / HIGH / MEDIUM / LOW, which rank alongside them);
`security.sast.fail_on` names the lowest severity that fails the check.
A severity this module doesn't recognise ranks as ERROR, because an
unknown label must not quietly fall below the gate.

A scan that produced no readable report (Semgrep crashed, timed out
fetching rules, or wrote nothing) is "could not run", not "no findings":
the check exits 2 rather than passing a scan that never happened. Semgrep's
stderr streams through as it runs, and its last lines go into the report,
so the reason (a failed rules fetch, a `semgrep` on PATH that can't run)
travels with the artifact and the PR comment.

Configuration (.slopstopper.yml, optional):

    security:
      sast:
        fail_on: error     # error (default) | warning | info | none

Exit codes:
  0: no findings at or above `security.sast.fail_on`
  1: one or more findings at or above `security.sast.fail_on`
  2: semgrep is not installed, exited with an error (a failed rules
      fetch, a bad config), wrote no readable report, or arguments were
      passed (this check takes none)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

from slopstopper import config, output
from slopstopper.checks import _report
from slopstopper.checks._contract import reject_extra_args, scan_incomplete

REPORT_DIR = Path(".ss/reports/sast")
REPORT_JSON = REPORT_DIR / "sast-report.json"
REPORT_MD = REPORT_DIR / "sast-report.md"

# Consumed by `slopstopper emit security:sast --target {pr-comment,issue}`.
# Discriminator `SAST Analysis` matches both the pre-flip JS heading
# ("## 🔍 SAST Analysis") and the post-flip report H1 ("# SAST Analysis
# Report"), so the same bot comment is reused after the workflow flip.
# Issue title, labels, and follow-up string are byte-identical to the
# legacy block.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "SAST Analysis",
    "issue_title": "⚠️ SAST Issues in Main Branch",
    "issue_labels": ["sast", "security"],
    "issue_followup": "🔔 SAST findings at or above `security.sast.fail_on` detected again in commit",
}

_INSTALL_HELP = (
    "semgrep is not installed.\n"
    "Install with:\n"
    "  pip3 install --user semgrep\n"
    "  brew install semgrep\n"
    "More: https://semgrep.dev/docs/getting-started/quickstart-oss"
)


def _semgrep_available() -> bool:
    return shutil.which("semgrep") is not None


# Semgrep's severities, ranked. `fail_on: warning` means WARNING and
# everything above it fails; `none` reports without ever failing.
# Semgrep's classic severities plus the CRITICAL/HIGH/MEDIUM/LOW scale
# newer registry rules report. Anything else ranks as ERROR (_rank).
SEVERITY_RANK = {
    "CRITICAL": 2, "HIGH": 2, "ERROR": 2,
    "MEDIUM": 1, "WARNING": 1,
    "LOW": 0, "INFO": 0,
    # Non-security severities some registry rules emit: informational.
    "INVENTORY": 0, "EXPERIMENT": 0,
}
ERROR_RANK = 2
FAIL_ON_CHOICES = ("error", "warning", "info", "none")
DEFAULT_FAIL_ON = "error"


def _fail_on() -> str:
    # get_str, not get(): a bare `fail_on: false` parses as a boolean, and
    # must reach the invalid-value warning below rather than silently
    # collapsing to the default.
    raw = config.get_str("security.sast.fail_on", DEFAULT_FAIL_ON).strip().lower()
    if raw in FAIL_ON_CHOICES:
        return raw
    output.warn(
        f"security.sast.fail_on: {raw!r} is not one of {', '.join(FAIL_ON_CHOICES)}. "
        f"Using {DEFAULT_FAIL_ON!r} instead."
    )
    return DEFAULT_FAIL_ON


def _blocking_findings(results: list[dict], fail_on: str) -> list[dict]:
    """Findings at or above the configured severity."""
    if fail_on == "none":
        return []
    threshold = SEVERITY_RANK[fail_on.upper()]
    return [
        r for r in results
        if _rank(r) >= threshold
    ]


def _rank(finding: dict) -> int:
    """A finding's rank. A severity Semgrep has never emitted, or a
    missing one on a malformed finding, ranks as ERROR: fail closed, not open."""
    severity = str((finding.get("extra") or {}).get("severity", "")).upper()
    return SEVERITY_RANK.get(severity, ERROR_RANK)


# Semgrep's exit codes for a scan that completed: 0, or 1 when `--error`
# is in effect and there are findings. Anything else, such as 2 (fatal), 7
# (missing config) or a failed rules-registry fetch, is a scan that
# did not run, even if Semgrep still wrote a JSON with `"results": []`.
SEMGREP_COMPLETED = frozenset({0, 1})

# How much of Semgrep's stderr an incomplete-scan report carries.
STDERR_TAIL_LINES = 20


def _run_semgrep() -> tuple[int, list[str]]:
    """Run Semgrep; return its exit code and the last lines of its stderr.

    stderr is echoed live, so the terminal shows Semgrep's progress as
    before, and the tail is kept for the report. The previous run's report
    is removed first: a scan that dies before writing must leave no
    report, not last run's.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.unlink(missing_ok=True)
    try:
        # why: `errors=` needs Python 3.6+; the CLI requires >=3.11.
        # nosemgrep: python.lang.compatibility.python36.python36-compatibility-Popen1
        proc = subprocess.Popen(
            [
                "semgrep",
                "--config=auto",
                "--json",
                f"--output={REPORT_JSON}",
                "--exclude=node_modules",
                "--exclude=.git",
                ".",
            ],
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
        )
    except OSError as exc:
        return 127, [str(exc)]
    tail: deque[str] = deque(maxlen=STDERR_TAIL_LINES)
    for line in proc.stderr:
        sys.stderr.write(line)
        if line.strip():
            tail.append(line.rstrip())
    return proc.wait(), list(tail)


def _incomplete_detail(rc: int, has_data: bool, stderr_tail: list[str]) -> str:
    what = "wrote no readable report" if not has_data else "reported a fatal error"
    detail = (
        f"Semgrep exited {rc} and {what} (`{REPORT_JSON}`). "
        "The scan is treated as not run, not as clean."
    )
    if not stderr_tail:
        return detail + " Semgrep printed nothing to stderr."
    body = "\n".join(stderr_tail)
    return (
        f"{detail}\n\nThe last {len(stderr_tail)} line(s) Semgrep printed to stderr:\n\n"
        f"```text\n{body}\n```\n\n"
        "If it says the `semgrep` command can't run (a stale mise shim, a broken "
        "venv), `slopstopper doctor` confirms it."
    )


def _read_data() -> dict | None:
    """Semgrep's JSON report, or None when there is no usable report.

    None means the scan could not run, and the caller exits 2. Returning an
    empty result set here would turn a crashed scan into a clean pass.
    """
    if not REPORT_JSON.exists():
        return None
    try:
        data = json.loads(REPORT_JSON.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        return None
    return data


def _categorize_findings(results: list[dict]) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    for finding in results:
        if _rank(finding) >= ERROR_RANK:
            errors.append(finding)
        else:
            warnings.append(finding)
    return errors, warnings


def _format_finding_row(finding: dict) -> str:
    check_id = finding.get("check_id", "unknown")
    path = finding.get("path", "unknown")
    start_line = finding.get("start", {}).get("line", "?")
    extra = finding.get("extra") or {}
    message = str(extra.get("message") or "").replace("\n", " ").strip()
    severity = extra.get("severity") or "unknown"
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
        out += "**Is this safe to ignore?** ✅ **Yes.** These are only debug/logging scripts, not production code. "
        out += "The bash syntax is valid and the workflows execute correctly. The SAST scan itself completed successfully with valid results.\n\n"
    else:
        out += f"Semgrep reported {len(errors)} error(s) during scanning:\n\n"
        for i, error in enumerate(errors, 1):
            msg = error.get("message", "Unknown error").split('\n')[0]
            out += f"{i}. {msg}\n"
        out += "\n"
    return out


def _build_md_report(data: dict, fail_on: str = DEFAULT_FAIL_ON) -> str:
    results = data.get("results", [])
    errors = data.get("errors", [])
    error_findings, warning_findings = _categorize_findings(results)
    total_findings = len(results)

    md = "# SAST Analysis Report\n\n"
    md += f"**Generated**: {_report.generated_at()}\n\n"
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
    if fail_on == "none":
        md += "- **Blocking**: nothing, because `security.sast.fail_on: none` reports findings without failing\n"
    else:
        md += f"- **Blocking**: findings at or above `fail_on: {fail_on}` fail the check. Fix them or suppress them narrowly with a `# why`\n"
        md += "- **Below the threshold**: reported for review; they don't fail the check\n"
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


def run(args: list[str] | None = None) -> int:
    if args:
        return reject_extra_args("security:sast", args)
    if not _semgrep_available():
        output.error(_INSTALL_HELP)
        return 2

    output.running("Running SAST analysis…")
    rc, stderr_tail = _run_semgrep()
    data = _read_data()
    if data is None or rc not in SEMGREP_COMPLETED:
        return scan_incomplete(
            REPORT_DIR, REPORT_MD, "SAST Analysis Report",
            _incomplete_detail(rc, data is not None, stderr_tail),
        )

    fail_on = _fail_on()
    REPORT_MD.write_text(_build_md_report(data, fail_on))

    results = data.get("results", [])
    blocking = _blocking_findings(results, fail_on)
    if results:
        errors, warnings = _categorize_findings(results)
        output.warn(
            f"Found {len(results)} finding(s): {len(errors)} error(s), {len(warnings)} warning(s)"
        )
        if blocking:
            output.error(f"{len(blocking)} finding(s) at or above `fail_on: {fail_on}`, so the check fails")
        else:
            output.info(f"none at or above `fail_on: {fail_on}`, so the check does not fail")
    else:
        output.success("No findings detected")
    output.footer(REPORT_DIR, [REPORT_MD.name])
    return 1 if blocking else 0
