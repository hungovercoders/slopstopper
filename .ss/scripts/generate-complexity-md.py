#!/usr/bin/env python3
"""Generate a Markdown complexity report from Lizard's CSV output.

Read the CSV produced by `python3 -m lizard . --csv` and emit a single
Markdown report with a summary section, a high-complexity table (CCN > 10),
and guidelines. Compute the summary stats (total NLOC, averages, function
count, warning count) directly from the CSV rows — Lizard's CLI output
formats are mutually exclusive so consuming a separate text file would
mean scanning the codebase twice.
"""

import os
import csv
from datetime import datetime
import sys
import traceback


CCN_THRESHOLD = 10


def read_csv_rows(csv_path):
    """Read the CSV report and return [(nloc, ccn, tokens, params, length, location, file), ...].

    Lizard's CSV layout (zero-indexed):
      0: NLOC, 1: CCN, 2: tokens, 3: params, 4: length,
      5: location ("function@start-end@./path"), 6: file path,
      7: function name, 8: long name, 9: start_line, 10: end_line

    Skips any leading header row (lizard's --csv output is headerless, but
    fixtures sometimes include one — non-numeric rows are dropped).
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV report not found at {csv_path}")

    rows = []
    try:
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
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
                else:
                    # Fallback: lizard's location is "function@start-end@./path";
                    # take the last @-segment as the file. Older fixtures use
                    # "path:line" — fall back to the pre-colon prefix in that case.
                    if "@" in location:
                        file_path = location.split("@")[-1]
                    else:
                        file_path = location.split(":")[0]
                rows.append((nloc, ccn, tokens, params, length, location, file_path))
    except Exception as e:
        raise RuntimeError(f"Failed to read CSV report: {e}") from e

    return rows


def compute_summary_lines(rows):
    """Build a lizard-style summary block from CSV rows."""
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


def format_summary_section(summary_lines):
    if not summary_lines:
        return ""
    result = "```\n"
    result += "\n".join(summary_lines)
    result += "\n```\n\n"
    return result


def format_high_complexity_section(rows):
    high = [r for r in rows if r[1] > CCN_THRESHOLD]
    if not high:
        return "## ✅ Complexity Status\n\nNo high-complexity items found (all CCN ≤ 10)\n\n"

    result = "## ⚠️ High Complexity Items (CCN > 10)\n\n"
    result += "| NLOC | CCN | Tokens | Params | Length | Location |\n"
    result += "|------|-----|--------|--------|--------|----------|\n"
    for nloc, ccn, tokens, params, length, location, _file in high:
        result += f"| {nloc} | {ccn} | {tokens} | {params} | {length} | `{location}` |\n"
    return result


def build_markdown_report(rows):
    summary_lines = compute_summary_lines(rows)

    md_content = "# Code Complexity Analysis Report\n\n"
    md_content += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md_content += "## Summary\n\n"
    md_content += format_summary_section(summary_lines)
    md_content += format_high_complexity_section(rows)

    md_content += "## Guidelines\n\n"
    md_content += "- **Cyclomatic Complexity (CCN)**: Measure of code complexity based on decision points\n"
    md_content += "  - **Good**: CCN ≤ 10\n"
    md_content += "  - **Warning**: 10 < CCN ≤ 15\n"
    md_content += "  - **Critical**: CCN > 15\n\n"
    md_content += "- **Function Length (NLOC)**: Number of lines of code\n"
    md_content += "  - Target: Keep functions under 50 lines\n"
    md_content += "  - For this static template, code should be minimal\n\n"
    md_content += "- **Threshold**: Any function with CCN > 10 should be reviewed and simplified\n\n"
    md_content += "## More Information\n\n"
    md_content += "- Generated by [Lizard](http://www.lizard.ws/)\n"
    md_content += "- Reports location: `.ss/reports/complexity/`\n"
    md_content += "  - `complexity-report.md` (this file)\n"
    md_content += "  - `complexity-report.csv` (machine-readable)\n"

    return md_content


def write_report(report_path, content):
    try:
        with open(report_path, "w") as f:
            f.write(content)
    except Exception as e:
        raise RuntimeError(f"Failed to write markdown report: {e}") from e


def main():
    os.makedirs(".ss/reports/complexity", exist_ok=True)

    csv_path = ".ss/reports/complexity/complexity-report.csv"
    report_path = ".ss/reports/complexity/complexity-report.md"

    rows = read_csv_rows(csv_path)
    report_content = build_markdown_report(rows)
    write_report(report_path, report_content)

    print("✅ Markdown report generated successfully")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Error generating markdown report: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
