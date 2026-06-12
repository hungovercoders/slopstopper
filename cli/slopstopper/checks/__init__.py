"""Check registry. Maps `<category>:<name>` keys to check entrypoints."""

from __future__ import annotations

from typing import Callable, Optional

from slopstopper.checks import (
    complexity,
    csp_exceptions,
    dast,
    dependencies,
    docs_accuracy,
    docs_size,
    docs_structure,
    entry_files,
    sast,
    secrets,
    smoke,
)

REGISTRY: dict[str, Callable[[Optional[list[str]]], int]] = {
    "hygiene:complexity": complexity.run,
    "hygiene:csp-exceptions": csp_exceptions.run,
    "hygiene:docs-accuracy": docs_accuracy.run,
    "hygiene:docs-size": docs_size.run,
    "hygiene:docs-structure": docs_structure.run,
    "hygiene:entry-files": entry_files.run,
    "reliability:smoke": smoke.run,
    "security:dast": dast.run,
    "security:dependencies": dependencies.run,
    "security:sast": sast.run,
    "security:secrets": secrets.run,
}
