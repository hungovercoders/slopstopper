"""Code complexity analyzer (Lizard wrapper).

Ports the bash hygiene:complexity flow:

  .ss/scripts/check-tool   (in Taskfile.ss.yml — installs lizard)
  + python3 -m lizard . ... --csv > complexity-report.csv
  + .ss/scripts/generate-complexity-md.py

into one self-contained check. Subprocess-invokes `python -m lizard`
(using sys.executable so the same Python running the CLI provides
lizard), captures the CSV, parses it, writes both the CSV and the
markdown report.

This is the CLI's first external-tool integration. Subprocess-invoke
boundary is the load-bearing licensing rule (see plan doc): we call
lizard's CLI, never `import lizard`. Adopter installs lizard
themselves (or via the test extra in cli/pyproject.toml's [test]
group, which is what CI does).

Exit codes:
  0 — analysis completed (independent of whether high-complexity items
      exist — gating happens at the workflow level, mirroring bash)
  1 — lizard is not installed
"""

from __future__ import annotations

import csv
import io
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path(".ss/reports/complexity")
REPORT_CSV = REPORT_DIR / "complexity-report.csv"
REPORT_MD = REPORT_DIR / "complexity-report.md"

# Exclude tests, generated files, vendored deps from the scan. Same list
# as Taskfile.ss.yml's hygiene:complexity:analyze.
LIZARD_EXCLUDES = (
    "tests/*",
    ".ss/tests/*",
    ".github/*",
    "node_modules/*",
    ".git/*",
)

CCN_THRESHOLD = 10

_LIZARD_INSTALL_HELP = (
    "❌ lizard is not installed.\n"
    "Install with:\n"
    "  pip3 install --user lizard\n"
    "  python3 -m pip install --user lizard\n"
    "Note: do NOT install via 'brew install lizard' — that's lz4's lizard,\n"
    "a completely different tool that will shadow the Python package."
)


def _lizard_available() -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "lizard", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def _run_lizard(target_dir: str = ".") -> str:
    """Invoke `python -m lizard <target> --csv ...` and return stdout."""
    cmd = [sys.executable, "-m", "lizard", target_dir]
    for ex in LIZARD_EXCLUDES:
        cmd += ["-x", ex]
    cmd += ["--csv"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout


def _parse_csv_rows(csv_text: str) -> list[tuple]:
    """Parse lizard's CSV output.

    Columns (0-indexed):
      0 nloc, 1 ccn, 2 tokens, 3 params, 4 length,
      5 location ("function@start-end@./path"),
      6 file path, 7 function name, 8 long name, ...

    Returns [(nloc, ccn, tokens, params, length, location, file), ...].
    Rows with non-numeric leading columns (header rows from fixtures) are
    silently skipped.
    """
    rows: list[tuple] = []
    reader = csv.reader(io.StringIO(csv_text))
    for row in reader:
        if len(row) < 6:
            continue
        try:
            nloc = int(row[0])
            ccn = int(row[1])
            tokens = int(row[2])
            params = int(row[3])
            length = int(row[4])
        except ValueError:
            continue
        location = row[5].strip('"')
        if len(row) > 6 and row[6]:
            file_path = row[6].strip('"')
        elif "@" in location:
            file_path = location.split("@")[-1]
        else:
            file_path = location.split(":")[0]
        rows.append((nloc, ccn, tokens, params, length, location, file_path))
    return rows


def _compute_summary_lines(rows: list[tuple]) -> list[str]:
    if not rows:
        return [
            "Total NLOC   Avg.NLOC  Avg.CCN  Avg.Tokens  Fun Cnt  Warning Cnt",
            "----------------------------------------------------------------",
            "         0        0.0      0.0         0.0        0            0",
            "",
            "No functions analyzed.",
        ]

    fun_cnt = len(rows)
    total_nloc = sum(r[0] for r in rows)
    avg_nloc = total_nloc / fun_cnt
    avg_ccn = sum(r[1] for r in rows) / fun_cnt
    avg_tokens = sum(r[2] for r in rows) / fun_cnt
    warning_cnt = sum(1 for r in rows if r[1] > CCN_THRESHOLD)

    files = {r[6] for r in rows}
    file_count = len(files)
    file_word = "file" if file_count == 1 else "files"

    return [
        "Total NLOC   Avg.NLOC  Avg.CCN  Avg.Tokens  Fun Cnt  Warning Cnt",
        "----------------------------------------------------------------",
        f"{total_nloc:>10}  {avg_nloc:>9.1f}  {avg_ccn:>7.1f}  {avg_tokens:>10.1f}  {fun_cnt:>7}  {warning_cnt:>11}",
        "",
        f"{file_count} {file_word} analyzed.",
    ]


def _format_summary_section(summary_lines: list[str]) -> str:
    if not summary_lines:
        return ""
    return "```\n" + "\n".join(summary_lines) + "\n```\n\n"


def _format_high_complexity_section(rows: list[tuple]) -> str:
    high = [r for r in rows if r[1] > CCN_THRESHOLD]
    if not high:
        return "## ✅ Complexity Status\n\nNo high-complexity items found (all CCN ≤ 10)\n\n"

    out = "## ⚠️ High Complexity Items (CCN > 10)\n\n"
    out += "| NLOC | CCN | Tokens | Params | Length | Location |\n"
    out += "|------|-----|--------|--------|--------|----------|\n"
    for nloc, ccn, tokens, params, length, location, _file in high:
        out += f"| {nloc} | {ccn} | {tokens} | {params} | {length} | `{location}` |\n"
    return out


def _generated_at() -> str:
    # Bash uses `datetime.now().strftime(...)` (naive local time). The
    # parity test strips this line so format is irrelevant, but using
    # timezone.utc here matches what the docs-size port chose.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _build_md_report(rows: list[tuple]) -> str:
    summary = _compute_summary_lines(rows)
    md = "# Code Complexity Analysis Report\n\n"
    md += f"**Generated**: {_generated_at()}\n\n"
    md += "## Summary\n\n"
    md += _format_summary_section(summary)
    md += _format_high_complexity_section(rows)
    md += "## Guidelines\n\n"
    md += "- **Cyclomatic Complexity (CCN)**: Measure of code complexity based on decision points\n"
    md += "  - **Good**: CCN ≤ 10\n"
    md += "  - **Warning**: 10 < CCN ≤ 15\n"
    md += "  - **Critical**: CCN > 15\n\n"
    md += "- **Function Length (NLOC)**: Number of lines of code\n"
    md += "  - Target: Keep functions under 50 lines\n"
    md += "  - For this static template, code should be minimal\n\n"
    md += "- **Threshold**: Any function with CCN > 10 should be reviewed and simplified\n\n"
    md += "## More Information\n\n"
    md += "- Generated by [Lizard](http://www.lizard.ws/)\n"
    md += "- Reports location: `.ss/reports/complexity/`\n"
    md += "  - `complexity-report.md` (this file)\n"
    md += "  - `complexity-report.csv` (machine-readable)\n"
    return md


def run(_args: list[str] | None = None) -> int:
    if not _lizard_available():
        print(_LIZARD_INSTALL_HELP)
        return 1

    print("🔍 Analyzing code complexity…")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    csv_text = _run_lizard()
    REPORT_CSV.write_text(csv_text)

    rows = _parse_csv_rows(csv_text)
    REPORT_MD.write_text(_build_md_report(rows))

    high_count = sum(1 for r in rows if r[1] > CCN_THRESHOLD)
    if high_count:
        print(f"⚠️  Found {high_count} item(s) with cyclomatic complexity > 10")
    else:
        print("✅ No high-complexity items found (all CCN ≤ 10)")

    print(f"📁 Reports saved to: {REPORT_DIR}/")
    print(f"   • {REPORT_MD.name}")
    print(f"   • {REPORT_CSV.name}")
    return 0
