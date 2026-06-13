"""Template-file resolution for the reliability checks.

The CLI ships Playwright specs, the Playwright config and the Lighthouse
CI config as package data under cli/slopstopper/data/. Adopters can
still override any of these by writing the same-named file under .ss/
in their repo — the resolver looks at the override path first and falls
back to the package-data copy.

This means adopters who want defaults don't have to vendor those files
into their repo at all; the CLI brings them. Adopters who want to
customise drop a file under .ss/ (use `slopstopper templates eject
<name>` to copy the bundled file as a starting point) and the resolver
picks it up.

Single source of truth: cli/slopstopper/data/.
"""

from __future__ import annotations

import shutil
from pathlib import Path

PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"
OVERRIDE_ROOT = Path(".ss")

PLAYWRIGHT_CONFIG_NAME = "playwright.config.js"
LIGHTHOUSERC_NAME = "lighthouserc.json"
LIGHTHOUSERC_PROD_NAME = "lighthouserc.prod.json"


# ── inventory ────────────────────────────────────────────────────
#
# Each entry maps a template name (the public API for `slopstopper
# templates`) to (package-data path, adopter-override path relative to
# repo root). The override path doubles as the eject destination and as
# the lookup path for the resolver.

TEMPLATES: dict[str, tuple[Path, Path]] = {
    PLAYWRIGHT_CONFIG_NAME: (
        PACKAGE_DATA_DIR / PLAYWRIGHT_CONFIG_NAME,
        OVERRIDE_ROOT / PLAYWRIGHT_CONFIG_NAME,
    ),
    LIGHTHOUSERC_NAME: (
        PACKAGE_DATA_DIR / LIGHTHOUSERC_NAME,
        OVERRIDE_ROOT / LIGHTHOUSERC_NAME,
    ),
    LIGHTHOUSERC_PROD_NAME: (
        PACKAGE_DATA_DIR / LIGHTHOUSERC_PROD_NAME,
        OVERRIDE_ROOT / LIGHTHOUSERC_PROD_NAME,
    ),
    "tests/smoke.spec.ts": (
        PACKAGE_DATA_DIR / "tests" / "smoke.spec.ts",
        OVERRIDE_ROOT / "tests" / "smoke.spec.ts",
    ),
    "tests/accessibility.spec.ts": (
        PACKAGE_DATA_DIR / "tests" / "accessibility.spec.ts",
        OVERRIDE_ROOT / "tests" / "accessibility.spec.ts",
    ),
    "tests/broken-links.spec.ts": (
        PACKAGE_DATA_DIR / "tests" / "broken-links.spec.ts",
        OVERRIDE_ROOT / "tests" / "broken-links.spec.ts",
    ),
}


def list_templates() -> list[str]:
    """Return the sorted list of bundled template names."""
    return sorted(TEMPLATES)


def template_path(name: str) -> Path:
    """Resolve a template name: .ss/ override wins, else package data.

    Raises KeyError if the name isn't in the inventory.
    """
    src, override = TEMPLATES[name]
    return override if override.exists() else src


def is_ejected(name: str) -> bool:
    """True if the adopter has a `.ss/<name>` override on disk."""
    _, override = TEMPLATES[name]
    return override.exists()


def eject(name: str) -> tuple[Path, bool]:
    """Copy the bundled template into `.ss/<name>`.

    Returns (destination_path, was_new). was_new is False if a
    `.ss/<name>` was already there — we don't overwrite an existing
    override since the adopter may have customised it.

    Raises KeyError if the name isn't in the inventory.
    """
    src, override = TEMPLATES[name]
    if override.exists():
        return override, False
    override.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, override)
    return override, True


# ── back-compat thin wrappers used by the check modules ──────────


def playwright_config() -> Path:
    return template_path(PLAYWRIGHT_CONFIG_NAME)


def lighthouserc(prod: bool = False) -> Path:
    """Resolve the Lighthouse CI config path.

    ``prod=True`` picks the stricter `lighthouserc.prod.json` (extra
    asserts on accessibility / best-practices, plus speed-index and
    interactive). Used by the CWV check when the workflow is auditing
    a deployed URL on `deployment_status` or `schedule` events; the
    default `lighthouserc.json` is used on PR / push to main where the
    site is built locally.
    """
    return template_path(LIGHTHOUSERC_PROD_NAME if prod else LIGHTHOUSERC_NAME)


def playwright_spec(name: str) -> Path:
    """Resolve a Playwright spec by basename (without extension).

    Looks for .ss/tests/<name>.spec.ts first, then falls back to the
    bundled package-data spec.
    """
    return template_path(f"tests/{name}.spec.ts")
