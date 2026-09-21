"""Check registry. Maps `<category>:<name>` keys to check entrypoints.

Every entrypoint is `run(args: list[str] | None) -> int`, and the int is
the API. The contract, which every check's docstring restates for its
own cases and `cli/tests/test_exit_code_contract.py` enforces:

  0 — the check ran and found nothing to fail on. Includes a graceful
      skip: an unconfigured check is not a failing check.
  1 — the check ran and the repo failed it: findings over the threshold,
      drift, a budget exceeded, a required file that says the wrong
      thing. This is the verdict CI gates on.
  2 — the check could not run: a required tool is not installed, a
      required input is missing, a report came back unreadable, an
      unknown option or argument was passed. Not a verdict about the
      repo; something for the person running it to fix first.

Two checks used to blur this — `security:vulnerability:all` returned 2
for findings, and `security:sast` / `security:secrets` always returned
0 with the real verdict living in a Python heredoc inside their
workflow YAML, where no test could reach it.
"""

from __future__ import annotations

from typing import Callable, Optional

from slopstopper.checks import (
    accessibility,
    api_headers,
    api_health,
    api_latency,
    broken_links,
    complexity,
    csp_exceptions,
    cwv,
    dast,
    docs_accuracy,
    docs_size,
    docs_structure,
    entry_files,
    llms_txt,
    openapi,
    robots_txt,
    sast,
    secrets,
    seo,
    sitemap,
    smoke,
    vulnerability_all,
)

REGISTRY: dict[str, Callable[[Optional[list[str]]], int]] = {
    "hygiene:complexity": complexity.run,
    "hygiene:csp-exceptions": csp_exceptions.run,
    "hygiene:docs-accuracy": docs_accuracy.run,
    "hygiene:docs-size": docs_size.run,
    "hygiene:docs-structure": docs_structure.run,
    "hygiene:entry-files": entry_files.run,
    "hygiene:openapi": openapi.run,
    "reliability:accessibility": accessibility.run,
    "reliability:api-health": api_health.run,
    "reliability:api-latency": api_latency.run,
    "reliability:broken-links": broken_links.run,
    "reliability:cwv": cwv.run,
    "reliability:llms-txt": llms_txt.run,
    "reliability:robots-txt": robots_txt.run,
    "reliability:seo": seo.run,
    "reliability:sitemap": sitemap.run,
    "reliability:smoke": smoke.run,
    "security:api-headers": api_headers.run,
    "security:dast": dast.run,
    "security:sast": sast.run,
    "security:secrets": secrets.run,
    "security:vulnerability:all": vulnerability_all.run,
}
