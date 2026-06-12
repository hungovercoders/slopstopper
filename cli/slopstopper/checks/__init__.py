"""Check registry. Maps `<category>:<name>` keys to check entrypoints."""

from __future__ import annotations

from typing import Callable

from slopstopper.checks import docs_size

REGISTRY: dict[str, Callable[[], int]] = {
    "hygiene:docs-size": docs_size.run,
}
