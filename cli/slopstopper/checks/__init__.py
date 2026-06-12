"""Check registry. Maps `<category>:<name>` keys to check entrypoints."""

from __future__ import annotations

from typing import Callable

from slopstopper.checks import (
    complexity,
    csp_exceptions,
    docs_accuracy,
    docs_size,
    docs_structure,
    entry_files,
)

REGISTRY: dict[str, Callable[[], int]] = {
    "hygiene:complexity": complexity.run,
    "hygiene:csp-exceptions": csp_exceptions.run,
    "hygiene:docs-accuracy": docs_accuracy.run,
    "hygiene:docs-size": docs_size.run,
    "hygiene:docs-structure": docs_structure.run,
    "hygiene:entry-files": entry_files.run,
}
