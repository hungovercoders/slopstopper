"""Stand-ins for external tools, shared by the check tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

# What Playwright's JSON reporter writes when the suite ran and one test failed.
PLAYWRIGHT_FAILED_REPORT = {
    "errors": [],
    "stats": {"expected": 1, "unexpected": 1, "flaky": 0, "skipped": 0},
    "suites": [
        {
            "specs": [
                {"tests": [{"results": [{"status": "passed"}]}]},
                {"tests": [{"results": [{"status": "failed", "error": {"message": "expect(received).toBe(expected)"}}]}]},
            ]
        }
    ],
}


def playwright_failed(cmd, env, check):
    """`subprocess.run` for a Playwright suite that ran and had a failing test."""
    Path(env["PLAYWRIGHT_JSON_OUTPUT_NAME"]).write_text(json.dumps(PLAYWRIGHT_FAILED_REPORT))
    return subprocess.CompletedProcess(cmd, 1)
