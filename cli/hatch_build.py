"""Hatch build hook: ship the suite inside the wheel.

`slopstopper install` writes the workflows, shims, seeds, hook and skills
that live at the root of this repository, above `cli/`. A wheel built from
a checkout takes them from there; the sdist carries a copy under `suite/`
so a wheel built from the sdist (what `python -m build` does) finds the same
files. The list of what ships is `slopstopper.suite.shipped_paths`, so the
installer and the package can never disagree about it. An editable install
gets nothing copied: it reads the checkout directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PACKAGED = "slopstopper/data/suite"


class SuiteBuildHook(BuildHookInterface):
    PLUGIN_NAME = "suite"

    def initialize(self, version: str, build_data: dict) -> None:
        if version == "editable":
            return
        project = Path(self.root)
        sys.path.insert(0, str(project))
        from slopstopper import suite

        bundled = project / "suite"
        source = bundled if (bundled / suite.TASKFILE).is_file() else project.parent
        prefix = "suite" if self.target_name == "sdist" else PACKAGED
        for rel in suite.shipped_paths(source):
            build_data["force_include"][str(source / rel)] = f"{prefix}/{rel}"
