#!/usr/bin/env python3

"""Generate a Markdown documentation accuracy report from JSON output.

Reads .docs-reports/docs-accuracy-report.json (produced by check-docs-accuracy.py)
and writes .docs-reports/docs-accuracy-report.md — a human-readable summary.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    json_path = Path(".docs-reports/docs-accuracy-report.json")
    if not json_path.exists():
        print("❌ docs-accuracy-report.json not found — run check-docs-accuracy.py first")
        sys.exit(1)

    data = json.loads(json_path.read_text())
    issues = data.get("issues", [])
    is_clean = data.get("clean", True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# 🔎 Documentation Accuracy Report",
        "",
        f"**Generated:** {now}",
        "",
        "## Status",
        "",
    ]

    if is_clean:
        lines.append("✅ All documentation accuracy checks passed — no stale references detected.")
    else:
        lines.append(f"⚠️ Found **{len(issues)}** accuracy issue(s) that may need attention.")

    lines += ["", "## Issues", ""]

    if not issues:
        lines.append("No issues found.")
    else:
        # Group by type
        by_type = {}
        for issue in issues:
            by_type.setdefault(issue["type"], []).append(issue)

        type_labels = {
            "broken_link": "Broken Internal Links",
            "stale_task_ref": "Stale Taskfile References",
            "stale_workflow_ref": "Stale Workflow References",
            "stale_file_ref": "Possible Stale File References",
        }

        for itype, group in by_type.items():
            label = type_labels.get(itype, itype)
            lines.append(f"### {label}")
            lines.append("")
            for item in group:
                lines.append(f"- **{item['file']}** (line {item['line']}): {item['message']}")
            lines.append("")

    lines += [
        "## How to Fix",
        "",
        "1. Review each issue above.",
        "2. Update the referenced docs to match the current project state.",
        "3. Run `task hygiene:docs-accuracy` locally to verify fixes.",
        "",
    ]

    report_text = "\n".join(lines) + "\n"
    out = Path(".docs-reports/docs-accuracy-report.md")
    out.write_text(report_text)
    print(f"📄 Report written to {out}")


if __name__ == "__main__":
    main()
