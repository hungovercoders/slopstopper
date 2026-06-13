"""Template-file resolution for the reliability checks.

The CLI ships Playwright specs, the Playwright config and the Lighthouse
CI config as package data under cli/slopstopper/data/. Adopters can
still override any of these by writing the same-named file under .ss/
in their repo — the resolver looks at the override path first and falls
back to the package-data copy.

This means adopters who want defaults don't have to vendor those files
into their repo at all; the CLI brings them. Adopters who want to
customise drop a file under .ss/ and the resolver picks it up.

Single source of truth: cli/slopstopper/data/. The .ss/ copies that
slopstopper.dev (this repo) carries are dual-purposed today —
backwards-compat for adopters still on bash workflows, and the override
fixtures for our own dogfood CI. A separate hygiene gate keeps them in
sync with package data via cli/.../data/.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"

PLAYWRIGHT_CONFIG_NAME = "playwright.config.js"
LIGHTHOUSERC_NAME = "lighthouserc.json"
LIGHTHOUSERC_PROD_NAME = "lighthouserc.prod.json"


def _override_dir() -> Path:
    """Adopter-side override root.

    Anything written under .ss/<same-name> wins over the package-data copy.
    Looked up at call time, not import time, so tests using `isolated_cwd`
    pick up the temporary cwd.
    """
    return Path(".ss")


def playwright_config() -> Path:
    """Resolve the Playwright config path: .ss/playwright.config.js override
    or fall back to the bundled package-data copy."""
    override = _override_dir() / PLAYWRIGHT_CONFIG_NAME
    if override.exists():
        return override
    return PACKAGE_DATA_DIR / PLAYWRIGHT_CONFIG_NAME


def lighthouserc(prod: bool = False) -> Path:
    """Resolve the Lighthouse CI config path.

    ``prod=True`` picks the stricter `lighthouserc.prod.json` (extra
    asserts on accessibility / best-practices, plus speed-index and
    interactive). Used by the CWV check when the workflow is auditing
    a deployed URL on `deployment_status` or `schedule` events; the
    default `lighthouserc.json` is used on PR / push to main where the
    site is built locally.
    """
    name = LIGHTHOUSERC_PROD_NAME if prod else LIGHTHOUSERC_NAME
    override = _override_dir() / name
    if override.exists():
        return override
    return PACKAGE_DATA_DIR / name


def playwright_spec(name: str) -> Path:
    """Resolve a Playwright spec by basename (without extension).

    Looks for .ss/tests/<name>.spec.ts first, then falls back to the
    bundled package-data spec.
    """
    filename = f"{name}.spec.ts"
    override = _override_dir() / "tests" / filename
    if override.exists():
        return override
    return PACKAGE_DATA_DIR / "tests" / filename
