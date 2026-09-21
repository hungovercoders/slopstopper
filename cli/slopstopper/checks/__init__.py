"""Check registry. Maps `<category>:<name>` keys to check entrypoints."""

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
