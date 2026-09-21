"""Argument handling shared by checks that take no arguments.

Nine checks are configured entirely through `.slopstopper.yml` and have
no flags of their own. They used to declare `run(_args)` and drop
whatever the CLI forwarded, so

    slopstopper run hygiene:complexity -- --max-ccn 5

ran with the config default and reported nothing — the user believed a
setting was in effect that never was. Under the exit-code contract in
`slopstopper.checks`, an argument a check can't honour is a
misconfiguration, and misconfiguration is exit 2.
"""

from __future__ import annotations

from slopstopper import output

EXIT_MISCONFIGURED = 2


def reject_extra_args(check_name: str, args: list[str]) -> int:
    """Refuse arguments a check has no parser for. Always returns 2."""
    output.error(
        f"{check_name} takes no arguments (got: {' '.join(args)}). "
        "It is configured through .slopstopper.yml — see the check's docstring "
        "or `slopstopper checks describe` for the keys it reads."
    )
    return EXIT_MISCONFIGURED
