"""Check registry. Maps `<category>:<name>` keys to check entrypoints."""

from __future__ import annotations

from typing import Callable

from slopstopper.checks import docs_size, docs_structure, entry_files

REGISTRY: dict[str, Callable[[], int]] = {
    "hygiene:docs-size": docs_size.run,
    "hygiene:docs-structure": docs_structure.run,
    "hygiene:entry-files": entry_files.run,
}
