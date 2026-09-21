"""Secrets detection (Gitleaks wrapper).

Ports the bash security:secrets flow into one self-contained check:

  task secrets:check-tool   (installs gitleaks if missing)
  + gitleaks detect --source=. --report-format=json --report-path=...
  + python3 .ss/scripts/generate-secrets-md.py

Subprocess-invokes `gitleaks` — the same licensing-boundary pattern as
complexity (lizard). Adopters install gitleaks themselves (MIT). The
slopstopper-cli wheel ships zero gitleaks code.

The JSON report is redacted before anything else can read it. Gitleaks'
native output carries the captured credential verbatim (`Secret`) and the
source line around it (`Match`, `Line`). Both reports are uploaded as CI
artifacts, which anyone with read access to the repo can download for the
retention window — so a check whose job is to contain a leak would
otherwise widen its audience. What survives is everything a human needs
to find and fix the finding (rule, file, line number, commit,
fingerprint) and nothing they'd need to use it.

Exit codes:
  0 — analysis completed (gating happens at the workflow level)
  1 — gitleaks is not installed
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from slopstopper import output

REPORT_DIR = Path(".ss/reports/secrets")
REPORT_JSON = REPORT_DIR / "secrets-report.json"
REPORT_MD = REPORT_DIR / "secrets-report.md"

# Consumed by `slopstopper emit security:secrets --target {pr-comment,issue}`.
# Discriminator substring `Secrets Detection` matches both the pre-flip JS
# heading ("## 🔑 Secrets Detection") and the post-flip report H1
# ("# Secrets Detection Report"), so the same bot comment is reused after
# the workflow flip. Issue title, labels, and follow-up string are
# byte-identical to the legacy block.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "Secrets Detection",
    "issue_title": "⚠️ Secrets Detected in Main Branch",
    "issue_labels": ["secrets", "security"],
    "issue_followup": "🔔 Secrets detected again in commit",
}

_INSTALL_HELP = (
    "gitleaks is not installed.\n"
    "Install with:\n"
    "  brew install gitleaks                   # macOS\n"
    "  sudo apt-get install gitleaks           # Debian/Ubuntu (recent versions)\n"
    "Or pre-built binary from https://github.com/gitleaks/gitleaks/releases"
)


def _gitleaks_available() -> bool:
    return shutil.which("gitleaks") is not None


def _run_gitleaks() -> None:
    """Invoke `gitleaks detect --source=. ...`.

    Exit code 1 from gitleaks means findings — that's expected and not an
    error of the check. We rely on report file content, not the exit code.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "gitleaks", "detect",
            "--source=.",
            "--report-format=json",
            f"--report-path={REPORT_JSON}",
        ],
        check=False,
    )


def _read_findings() -> list[dict]:
    if not REPORT_JSON.exists():
        return []
    content = REPORT_JSON.read_text().strip()
    if not content or content == "null":
        return []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


# Keys in gitleaks' native finding schema that carry the credential itself
# or the source text around it. Matched case-insensitively because the
# report code above already tolerates both `RuleID` and `ruleID` spellings.
REDACTED_KEYS = frozenset({"secret", "match", "line"})


def _redact_finding(finding: dict) -> dict:
    """The finding with every credential-bearing key removed."""
    return {k: v for k, v in finding.items() if k.lower() not in REDACTED_KEYS}


def _redact_findings(findings: list[dict]) -> list[dict]:
    return [_redact_finding(f) if isinstance(f, dict) else f for f in findings]


def _write_redacted_json(findings: list[dict]) -> None:
    """Overwrite gitleaks' report with the redacted findings.

    Always rewrites when gitleaks produced a file, including the
    malformed case (which `_read_findings` reads as no findings): an
    unparseable report is still a file that may contain secrets, and
    the workflow gate counts it as zero either way.
    """
    if not REPORT_JSON.exists():
        return
    REPORT_JSON.write_text(json.dumps(findings, indent=2) + "\n")


def _format_finding_row(finding: dict) -> str:
    rule_id = finding.get("RuleID", finding.get("ruleID", "unknown"))
    description = finding.get("Description", finding.get("description", ""))
    file_path = finding.get("File", finding.get("file", "unknown"))
    line = finding.get("StartLine", finding.get("startLine", "?"))
    commit = finding.get("Commit", finding.get("commit", ""))
    short_commit = commit[:8] if commit else "working tree"
    location = f"`{file_path}:{line}`"
    desc_truncated = (description[:57] + "...") if len(description) > 60 else description
    return f"| {rule_id} | {location} | {short_commit} | {desc_truncated} |"


def _generated_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _build_md_report(findings: list[dict]) -> str:
    total = len(findings)
    md = "# Secrets Detection Report\n\n"
    md += f"**Generated**: {_generated_at()}\n\n"
    md += "## Summary\n\n"
    if total == 0:
        md += "## ✅ Secrets Status\n\nNo secrets detected.\n\n"
    else:
        md += f"> ⚠️ **{total} secret(s) detected** — revoke and remove immediately.\n\n"
        md += "| Rule | Location | Commit | Description |\n"
        md += "|------|----------|--------|-------------|\n"
        for finding in findings:
            md += _format_finding_row(finding) + "\n"
        md += "\n"
    md += "## Guidelines\n\n"
    md += "- **If secrets are found**: Revoke the credential immediately, then remove it from the codebase and git history\n"
    md += "- Use environment variables or a secrets manager instead of hardcoding credentials\n"
    md += "- Consider adding a `.gitleaks.toml` to tune rules for your project\n"
    md += "- Run `task secrets` locally before pushing to catch issues early\n\n"
    md += "## More Information\n\n"
    md += "- Generated by [Gitleaks](https://gitleaks.io/)\n"
    md += "- Reports location: `.ss/reports/secrets/`\n"
    md += "  - `secrets-report.md` (this file)\n"
    md += "  - `secrets-report.json` (machine-readable; secret values redacted)\n"
    return md


def run(_args: list[str] | None = None) -> int:
    if not _gitleaks_available():
        output.error(_INSTALL_HELP)
        return 1

    output.status("🔑", "Running secrets detection…")
    _run_gitleaks()
    findings = _redact_findings(_read_findings())
    _write_redacted_json(findings)
    REPORT_MD.write_text(_build_md_report(findings))

    if findings:
        output.warn(f"Found {len(findings)} secret(s) — revoke and remove immediately")
    else:
        output.success("No secrets detected")
    output.footer(REPORT_DIR, [REPORT_MD.name])
    return 0
