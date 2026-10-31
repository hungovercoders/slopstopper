"""Licence inventory over the full resolved dependency tree.

The licence policy is the repo's allowlist in
`.github/dependency-review-config.yml`, which `install.sh` seeds and the
dependency-review workflow applies to each PR's manifest diff. That gate
never sees a transitive dependency already in the lockfile, so a denied
licence that arrived before the policy did, or deep in a tree, stays
invisible. This check reads the same policy and applies it to everything
the lockfiles resolve to.

No tool is installed for it:

  - npm: `package-lock.json` (lockfile version 2 or 3) records every
    resolved package's `license`, so the tree is read from the lockfile
    alone, with no `node_modules` and no network. Dev dependencies are
    skipped unless `include_dev` is on, matching what ships.
  - Python: `python3 -m pip inspect` lists the packages installed in that
    interpreter's environment with their metadata, which is where a
    Python project's resolved tree lives. The check refuses to pass when
    neither the manifest's declared runtime dependencies nor the project
    itself is installed there, so an empty environment never reads as
    clean; a project that declares no runtime dependencies judges nothing
    and passes. Optional extras and Poetry dependency groups do not ship,
    so they count only when `include_dev` is on.

A licence the metadata does not state, or states in a form that is not
an SPDX expression, is listed as unknown and never fails the run, the
same rule the dependency-review action applies. A package named in the
policy's `allow-dependencies-licenses` (as a purl, `pkg:npm/<name>` or
`pkg:pypi/<name>`) is exempt whatever its licence.

Configuration (.slopstopper.yml):

    security:
      licences:
        policy: .github/dependency-review-config.yml  # the allowlist dependency review reads
        include_dev: false    # also judge npm devDependencies, Python extras and Poetry groups
        python: python3       # interpreter whose environment holds the Python dependencies

Exit codes:
  0: every resolved dependency's licence is on the allowlist (unknown
     licences are reported, not failed), or there is nothing to inventory
  1: a dependency carries a licence outside the policy
  2: no policy file, a lockfile too old to carry licences, `pip inspect`
     unavailable, a Python manifest whose dependencies are not installed,
     or arguments were passed (this check takes none)
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import unquote

from slopstopper import config, output
from slopstopper.checks import _report
from slopstopper.checks._contract import reject_extra_args, scan_incomplete

CHECK_NAME = "security:licences"
REPORT_DIR = Path(".ss/reports/licences")
REPORT_JSON = REPORT_DIR / "licences-report.json"
REPORT_MD = REPORT_DIR / "licences-report.md"
DEFAULT_POLICY = ".github/dependency-review-config.yml"

# Consumed by `slopstopper emit security:licences --target {pr-comment,issue}`.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "Licence Inventory",
    "issue_title": "⚖️ Dependency licence outside the allowlist on main",
    "issue_labels": ["dependencies", "security"],
    "issue_followup": "🔔 A dependency licence outside the allowlist detected again in commit",
    "issue_close_comment": "✅ Every dependency licence is on the allowlist again on `main`. Closing automatically.",
}

SKIP_DIRS = {"node_modules", ".git", ".ss", ".venv", "venv", "dist", "build"}
PYTHON_MANIFESTS = ("pyproject.toml", "requirements.txt")

# PyPI classifiers → SPDX, for packages that state their licence only
# that way. Anything else is unknown, not denied.
CLASSIFIER_SPDX = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: BSD License": "BSD-3-Clause",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)": "GPL-2.0-only",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)": "LGPL-2.1-or-later",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
    "License :: OSI Approved :: GNU Affero General Public License v3": "AGPL-3.0-only",
    "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
    "License :: Public Domain": "CC0-1.0",
}
_SPDX_ID_RE = re.compile(r"^[A-Za-z0-9.+-]+$")

# SPDX ids the check recognises as licences. One outside this set and
# outside the policy is unknown, not denied: "BSD" or "Dual License" is a
# metadata gap, not a GPL.
KNOWN_SPDX = {x.lower() for x in (
    "0BSD", "AGPL-1.0-only", "AGPL-3.0-only", "AGPL-3.0-or-later", "Apache-1.1", "Apache-2.0", "Artistic-2.0",
    "BlueOak-1.0.0", "BSD-1-Clause", "BSD-2-Clause", "BSD-2-Clause-Patent", "BSD-2-Clause-Views", "BSD-3-Clause",
    "BSD-3-Clause-Clear", "BSD-4-Clause", "BSL-1.0", "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-NC-4.0",
    "CC0-1.0", "CDDL-1.0", "CECILL-2.1", "CPAL-1.0", "curl", "EPL-1.0", "EPL-2.0", "EUPL-1.2", "GPL-1.0-only",
    "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later", "HPND", "ISC", "LGPL-2.0-only",
    "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0-only", "LGPL-3.0-or-later", "MIT", "MIT-0", "MPL-1.1",
    "MPL-2.0", "MS-PL", "NCSA", "OFL-1.1", "OpenSSL", "OSL-3.0", "PostgreSQL", "PSF-2.0", "Python-2.0",
    "Ruby", "SSPL-1.0", "Unicode-3.0", "Unicode-DFS-2016", "Unlicense", "UPL-1.0", "W3C", "WTFPL", "X11",
    "Zlib", "ZPL-2.1", "BUSL-1.1", "Elastic-2.0", "CC-BY-NC-SA-4.0", "EUPL-1.1", "LPPL-1.3c", "MPL-2.0-no-copyleft-exception",
)}
# Free-text licence names metadata often carries, canonicalised (lower, no
# "license"/"version"/punctuation) → SPDX. Ambiguous ones ("BSD") are left out.
LICENCE_ALIASES = {
    "mit": "MIT", "apache 2": "Apache-2.0", "apache 20": "Apache-2.0", "apache2": "Apache-2.0", "apache": "Apache-2.0",
    "asl 2": "Apache-2.0", "python foundation": "PSF-2.0", "3 clause bsd": "BSD-3-Clause", "new bsd": "BSD-3-Clause", "modified bsd": "BSD-3-Clause",
    "bsd 3 clause": "BSD-3-Clause", "bsd 2 clause": "BSD-2-Clause", "simplified bsd": "BSD-2-Clause", "isc": "ISC",
    "mpl 2": "MPL-2.0", "mpl 20": "MPL-2.0", "mozilla public 2": "MPL-2.0", "psf": "PSF-2.0", "python software foundation": "PSF-2.0",
    "zlib": "Zlib", "zlib libpng": "Zlib", "unlicense": "Unlicense", "public domain": "CC0-1.0", "cc0": "CC0-1.0",
    "gpl 3": "GPL-3.0-only", "gplv3": "GPL-3.0-only", "gpl 2": "GPL-2.0-only", "gplv2": "GPL-2.0-only",
    "lgpl 3": "LGPL-3.0-only", "lgplv3": "LGPL-3.0-only", "lgpl 21": "LGPL-2.1-only", "agpl 3": "AGPL-3.0-only", "agplv3": "AGPL-3.0-only",
    "gnu general public 3": "GPL-3.0-only", "gnu general public 3 gplv3": "GPL-3.0-only", "gnu general public 2": "GPL-2.0-only",
    "gnu general public 2 gplv2": "GPL-2.0-only", "gnu lesser general public 3": "LGPL-3.0-only", "gnu lesser general public 21": "LGPL-2.1-only",
    "gnu affero general public 3": "AGPL-3.0-only", "gnu affero general public 3 agplv3": "AGPL-3.0-only",
}


_DEPRECATED_GNU_RE = re.compile(r"^((?:A|L)?GPL-\d\.\d)(\+)?$", re.I)


def _canonical(licence_id: str) -> str:
    """An SPDX id for a licence string: itself when it already is one, the
    current id for a deprecated GNU form (`GPL-3.0` → `GPL-3.0-only`,
    `GPL-2.0+` → `GPL-2.0-or-later`), the alias table's answer for a known
    free-text name, else the string."""
    raw = licence_id.strip()
    low = raw.lower()
    if low in KNOWN_SPDX:
        return raw
    gnu = _DEPRECATED_GNU_RE.match(raw)
    if gnu:
        return f"{gnu.group(1).upper()}{'-or-later' if gnu.group(2) else '-only'}"
    words = re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\b(the|license|licence|version|only|software)\b|\bv(?=\d)", " ", low.replace(".", "")))
    words = re.sub(r"\s+", " ", words).strip()
    return LICENCE_ALIASES.get(words, raw)


# ── the policy ──────────────────────────────────────────────────────


def _policy_path() -> Path:
    return Path(str(config.get("security.licences.policy", DEFAULT_POLICY) or DEFAULT_POLICY))


def _unquote(item: str) -> str:
    return item.strip().strip("'\"")


def _flow_list(rest: str) -> list[str] | None:
    """`[a, b]` as a list; None when `rest` is not a flow list."""
    if rest.startswith("[") and rest.endswith("]"):
        return [_unquote(x) for x in rest[1:-1].split(",") if x.strip()]
    return None


def _yaml_lists(text: str) -> dict[str, list[str]]:
    """The top-level `key:` lists of a flat YAML file, as block lists
    (`- item`, at any indentation) or flow lists (`[a, b]`), comments
    stripped. The config has no nesting, so a line reader is enough (the
    CLI carries no YAML parser)."""
    lists: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = re.sub(r"(^|\s)#.*$", "", raw).rstrip()
        if not line.strip():
            continue
        key = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if key:
            flow = _flow_list(key.group(2).strip())
            lists[key.group(1)] = flow if flow is not None else []
            current = None if flow is not None else key.group(1)
            continue
        item = re.match(r"^\s*-\s+(.+)$", line)
        if item and current:
            lists[current].append(_unquote(item.group(1)))
        else:
            current = None
    return lists


def _read_policy(path: Path) -> dict | None:
    """The policy, or None when the file carries neither an allow nor a
    deny list (nothing to judge against)."""
    lists = _yaml_lists(path.read_text(encoding="utf-8"))
    if "allow-licenses" not in lists and "deny-licenses" not in lists:
        return None
    return {
        "allow": {x.lower() for x in lists.get("allow-licenses", [])},
        "deny": {x.lower() for x in lists.get("deny-licenses", [])},
        "exempt": {_purl_key(x) for x in lists.get("allow-dependencies-licenses", [])},
    }


def _purl_key(purl: str) -> str:
    """`pkg:npm/%40scope/name@1.2` → `npm:@scope/name`."""
    body = re.split(r"[?#]", purl.split(":", 1)[-1], maxsplit=1)[0]
    ecosystem, _, name = body.partition("/")
    name = unquote(name)
    if "@" in name[1:]:
        name = name[0] + name[1:].split("@", 1)[0]
    return f"{ecosystem.lower()}:{_normalise_name(ecosystem, name)}"


def _normalise_name(ecosystem: str, name: str) -> str:
    if ecosystem == "pypi":
        return re.sub(r"[-_.]+", "-", name).lower()
    return name


# ── SPDX expressions ────────────────────────────────────────────────


def _tokens(expression: str) -> list[str]:
    return re.findall(r"\(|\)|[^\s()]+", expression)


def _allowed(expression: str, policy: dict) -> bool | None:
    """Whether an SPDX expression satisfies the policy; None when it is not
    an expression the check can read (an unknown licence)."""
    canonical = _canonical(expression)
    tokens = _tokens(canonical if canonical != expression.strip() else expression)
    if not tokens:
        return None
    try:
        verdict, rest = _parse_or(tokens, policy)
    except ValueError:
        return None
    return verdict if not rest else None


def _parse_or(tokens: list[str], policy: dict) -> tuple[bool | None, list[str]]:
    left, rest = _parse_and(tokens, policy)
    while rest and rest[0].upper() == "OR":
        right, rest = _parse_and(rest[1:], policy)
        left = _combine(left, right, any)
    return left, rest


def _parse_and(tokens: list[str], policy: dict) -> tuple[bool | None, list[str]]:
    left, rest = _parse_atom(tokens, policy)
    while rest and rest[0].upper() == "AND":
        right, rest = _parse_atom(rest[1:], policy)
        left = _combine(left, right, all)
    return left, rest


def _parse_atom(tokens: list[str], policy: dict) -> tuple[bool | None, list[str]]:
    if not tokens:
        raise ValueError("empty")
    if tokens[0] == "(":
        inner, rest = _parse_or(tokens[1:], policy)
        if not rest or rest[0] != ")":
            raise ValueError("unbalanced")
        return inner, rest[1:]
    licence_id = tokens[0]
    rest = tokens[1:]
    if len(rest) >= 2 and rest[0].upper() == "WITH":
        licence_id, rest = f"{licence_id} WITH {rest[1]}", rest[2:]
    if not _SPDX_ID_RE.match(licence_id.split(" ")[0]):
        raise ValueError("not an id")
    base, _, exception = licence_id.partition(" WITH ")
    base = _canonical(base)
    return _id_allowed(f"{base} WITH {exception}" if exception else base, policy), rest


def _id_allowed(licence_id: str, policy: dict) -> bool | None:
    """True/False against the policy; None for an id neither the policy nor
    the SPDX list knows (a metadata gap, reported but not failed)."""
    low = licence_id.lower()
    base = low.split(" with ")[0]
    if policy["deny"]:
        if low in policy["deny"] or base in policy["deny"]:
            return False
        return True if base in KNOWN_SPDX or low in policy["allow"] else None
    if low in policy["allow"] or base in policy["allow"]:
        return True
    # npm's UNLICENSED is an explicit "no grant", not a metadata gap.
    return False if base in KNOWN_SPDX or base == "unlicensed" else None


def _combine(a: bool | None, b: bool | None, how) -> bool | None:
    if a is None or b is None:
        return None
    return how((a, b))


# ── npm ─────────────────────────────────────────────────────────────


def _manifest_dirs(root: Path) -> list[Path]:
    return [root, *sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP_DIRS)]


def _npm_lockfiles(root: Path) -> list[Path]:
    return [d / "package-lock.json" for d in _manifest_dirs(root) if (d / "package-lock.json").is_file()]


def _licence_field(value: object) -> str | None:
    """npm's `license` is an SPDX expression; older packages used a list of
    `{type}` objects or a single object."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _licence_field(value.get("type"))
    if isinstance(value, list):
        types = [t for t in (_licence_field(v) for v in value) if t]
        return " OR ".join(types) if types else None
    return None


def _npm_packages(lockfile: Path, include_dev: bool) -> list[dict] | str:
    """The resolved npm packages, or a reason string when the lockfile
    cannot be read for licences."""
    try:
        data = json.loads(lockfile.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"`{lockfile}` is not readable JSON ({exc})"
    packages = data.get("packages") if isinstance(data, dict) else None
    if not isinstance(packages, dict):
        return f"`{lockfile}` is lockfile version {data.get('lockfileVersion', '?')}, which carries no licence data; run `npm install` with npm 7 or newer to rewrite it"
    out = []
    for path, entry in packages.items():
        # The root and workspace packages (no `node_modules/` in the path)
        # are the repo's own code, not dependencies.
        if not path or "node_modules/" not in path or not isinstance(entry, dict) or entry.get("link"):
            continue
        if entry.get("dev") and not include_dev:
            out.append({"ecosystem": "npm", "name": path.rsplit("node_modules/", 1)[-1], "dev_skipped": True})
            continue
        out.append({
            "ecosystem": "npm",
            "name": path.rsplit("node_modules/", 1)[-1],
            "version": str(entry.get("version", "?")),
            "licence": _licence_field(entry.get("license", entry.get("licenses"))),
            "source": str(lockfile),
        })
    return out


# ── Python ──────────────────────────────────────────────────────────


def _python_manifests(root: Path) -> list[Path]:
    return [d / m for d in _manifest_dirs(root) for m in PYTHON_MANIFESTS if (d / m).is_file()]


def _pyproject_specs(data: dict) -> tuple[list[str], list[str], set[str]]:
    """(runtime dependency specs, optional specs, project names) a parsed
    pyproject declares, from `[project]` and from Poetry's tables. The
    optional ones are `[project.optional-dependencies]` extras and Poetry's
    dependency groups: installed on request, not shipped (#578)."""
    project = data.get("project") or {}
    poetry = (data.get("tool") or {}).get("poetry") or {}
    projects = {_normalise_name("pypi", str(n)) for n in (project.get("name"), poetry.get("name")) if n}
    specs = list(project.get("dependencies", []))
    optional: list[str] = []
    for extra in (project.get("optional-dependencies") or {}).values():
        optional += list(extra)
    specs += [name for name in (poetry.get("dependencies") or {}) if name.lower() != "python"]
    for group in (poetry.get("group") or {}).values():
        optional += [name for name in (group.get("dependencies") or {}) if name.lower() != "python"]
    return specs, optional, projects


def _requirements_specs(text: str) -> list[str]:
    specs = [line.split("#", 1)[0].strip() for line in text.splitlines()]
    return [s for s in specs if s and not s.startswith("-")]


def _names(specs: list[str]) -> set[str]:
    names = set()
    for spec in specs:
        m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
        if m:
            names.add(_normalise_name("pypi", m.group(1)))
    return names


def _declared(manifest: Path, include_dev: bool = False) -> tuple[set[str], set[str], set[str]]:
    """(dependency names, project names, optional names left out) a manifest
    declares, normalised. With `include_dev` the optional names (extras,
    Poetry groups) count as declared and the third set is empty."""
    text = manifest.read_text(encoding="utf-8", errors="replace")
    projects: set[str] = set()
    optional: list[str] = []
    if manifest.name == "pyproject.toml":
        try:
            specs, optional, projects = _pyproject_specs(tomllib.loads(text))
        except tomllib.TOMLDecodeError:
            return set(), projects, set()
    else:
        specs = _requirements_specs(text)
    deps, extras = _names(specs), _names(optional)
    if include_dev:
        return deps | extras, projects, set()
    return deps, projects, extras - deps


def _python_licence(metadata: dict) -> str | None:
    """`License-Expression` first (PEP 639); else the `License` field when
    it reads as SPDX; else a licence classifier; else the field as written,
    which the judge will report as unknown."""
    expression = metadata.get("license_expression")
    if expression:
        return str(expression).strip()
    licence = str(metadata.get("license") or "").strip()
    short = licence and "\n" not in licence and len(licence) <= 60 and licence.upper() not in {"UNKNOWN", "LICENSE", "LICENSE.TXT", "SEE LICENSE"}
    if short and _canonical(licence).lower() in KNOWN_SPDX:
        return _canonical(licence)
    for classifier in metadata.get("classifier") or []:
        if classifier in CLASSIFIER_SPDX:
            return CLASSIFIER_SPDX[classifier]
    return licence if short else None


def _pip_inspect(python: str) -> list[dict] | str:
    try:
        proc = subprocess.run([python, "-m", "pip", "inspect"], capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"`{python} -m pip inspect` could not run ({exc})"
    if proc.returncode != 0:
        return f"`{python} -m pip inspect` exited {proc.returncode}; it needs pip 22.2 or newer ({(proc.stderr or '').strip().splitlines()[-1:] or ['no output']})"
    try:
        installed = json.loads(proc.stdout).get("installed", [])
    except ValueError:
        return f"`{python} -m pip inspect` printed no JSON"
    return [d.get("metadata", {}) for d in installed if isinstance(d, dict)]


def _python_interpreter(root: Path, manifests: list[Path]) -> str | None:
    """`security.licences.python` when set; else a virtualenv beside a
    manifest (`.venv/` or `venv/`), where a checkout's resolved tree
    lives; else `python3` on PATH, which is the environment CI installs
    the project into."""
    configured = config.get("security.licences.python")
    if configured:
        return shutil.which(str(configured)) or (str(root / str(configured)) if (root / str(configured)).is_file() else None)
    for manifest in manifests:
        for venv in (".venv", "venv"):
            for candidate in (manifest.parent / venv / "bin" / "python", manifest.parent / venv / "Scripts" / "python.exe"):
                if candidate.is_file():
                    return str(candidate)
    return shutil.which("python3")


def _python_packages(root: Path, manifests: list[Path], include_dev: bool = False) -> list[dict] | str:
    """The packages installed in the configured interpreter, once the
    manifests' declared runtime dependencies, or the project itself, are
    among them. A manifest that declares nothing the check can read judges
    nothing, rather than whatever environment happens to be on PATH; so
    does a project with no runtime dependencies, which is what an installed
    stdlib-only package resolves to (#578)."""
    python = _python_interpreter(root, manifests)
    if not python:
        return "no `python3` on PATH to inspect; set security.licences.python to the interpreter whose environment holds the project's dependencies"
    metadata = _pip_inspect(python)
    if isinstance(metadata, str):
        return metadata
    declared: set[str] = set()
    projects: set[str] = set()
    for manifest in manifests:
        d, p, _ = _declared(manifest, include_dev)
        declared |= d
        projects |= p
    installed = {_normalise_name("pypi", str(m.get("name", ""))): m for m in metadata if m.get("name")}
    if not declared:
        return []
    if not ((declared | projects) & set(installed)):
        return (
            f"none of the dependencies declared in {', '.join(f'`{m.relative_to(root)}`' for m in manifests)} is installed in "
            f"`{python}`'s environment, so there is no resolved tree to inventory; install the project there first "
            "(CI: a `pip install` step before this check), or point security.licences.python at the interpreter that has it"
        )
    return [
        {"ecosystem": "pypi", "name": name, "version": str(m.get("version", "?")), "licence": _python_licence(m), "source": python}
        for name, m in sorted(installed.items())
        if name not in projects
    ]


# ── evaluation and reports ──────────────────────────────────────────


def _judge(packages: list[dict], policy: dict) -> tuple[list[dict], list[dict]]:
    """(denied, unknown)."""
    denied, unknown = [], []
    for pkg in packages:
        if f"{pkg['ecosystem']}:{_normalise_name(pkg['ecosystem'], pkg['name'])}" in policy["exempt"]:
            pkg["exempt"] = True
            continue
        verdict = _allowed(pkg["licence"], policy) if pkg["licence"] else None
        if verdict is None:
            unknown.append(pkg)
        elif not verdict:
            denied.append(pkg)
    return denied, unknown


def _row(pkg: dict) -> str:
    return f"| `{pkg['name']}` | {pkg['version']} | {pkg['ecosystem']} | {pkg['licence'] or '(none stated)'} |"


def _build_md_report(result: dict) -> str:
    md = f"# Licence Inventory Report\n\n**Generated**: {_report.generated_at()}\n\n"
    md += f"**Policy**: `{result['policy']}`  ·  **Packages judged**: {result['judged']}"
    md += "".join(f"  ·  {eco}: {n}" for eco, n in sorted(result["per_ecosystem"].items())) + "\n\n"
    for reason in result["not_scanned"]:
        md += f"- ℹ️ {reason}\n"
    if result["not_scanned"]:
        md += "\n"
    if result["denied"]:
        md += f"## ❌ Outside the allowlist ({len(result['denied'])})\n\n| Package | Version | Ecosystem | Licence |\n|---|---|---|---|\n"
        md += "\n".join(_row(p) for p in result["denied"]) + "\n\n"
        md += ("Replace the package, or accept its licence for this project by adding its purl to `allow-dependencies-licenses` "
               f"in `{result['policy']}` with a comment saying why.\n\n")
    else:
        md += "## ✅ Every judged licence is on the allowlist\n\n"
    if result["unknown"]:
        md += f"## ℹ️ Licence not stated or not SPDX ({len(result['unknown'])})\n\nReported, never failed, as dependency review does.\n\n"
        md += "| Package | Version | Ecosystem | Licence |\n|---|---|---|---|\n"
        md += "\n".join(_row(p) for p in result["unknown"]) + "\n\n"
    md += f"- Run `task ss:{CHECK_NAME}` locally to reproduce\n- Reports: `{REPORT_DIR}/`\n"
    return md


def _inventory(root: Path, include_dev: bool) -> tuple[list[dict], list[str], list[str]]:
    """(packages, reasons nothing was scanned, hard failures)."""
    packages: list[dict] = []
    skipped: list[str] = []
    failures: list[str] = []
    for lockfile in _npm_lockfiles(root):
        found = _npm_packages(lockfile, include_dev)
        if isinstance(found, str):
            failures.append(found)
            continue
        dev = [p for p in found if p.get("dev_skipped")]
        if dev:
            skipped.append(f"`{lockfile.relative_to(root)}`: {len(dev)} devDependencies not judged (they do not ship; `security.licences.include_dev: true` judges them too)")
        packages += [p for p in found if not p.get("dev_skipped")]
    for name in ("yarn.lock", "pnpm-lock.yaml"):
        for d in _manifest_dirs(root):
            if (d / name).is_file():
                skipped.append(f"`{(d / name).relative_to(root)}` carries no licence data, so that tree was not judged")
    manifests = _python_manifests(root)
    if manifests:
        found = _python_packages(root, manifests, include_dev)
        if isinstance(found, str):
            failures.append(found)
        elif not found:
            skipped.append(f"{', '.join(f'`{m.relative_to(root)}`' for m in manifests)} declare no runtime dependencies the check can read, so no Python environment was judged")
        else:
            packages += found
            skipped.append(f"Python packages read from `{found[0]['source']}`")
        for manifest in manifests:
            _, _, optional = _declared(manifest, include_dev)
            if optional:
                skipped.append(f"`{manifest.relative_to(root)}`: {len(optional)} optional (extras / Poetry group) dependencies not judged (they do not ship; `security.licences.include_dev: true` judges them too)")
    return packages, skipped, failures


def _cannot_run(reasons: list[str]) -> int:
    """Say why on stdout, record it in the report, exit 2."""
    for reason in reasons:
        output.error(reason)
    return scan_incomplete(REPORT_DIR, REPORT_MD, "Licence Inventory Report", "\n\n".join(f"- {r}" for r in reasons))


def run(args: list[str] | None = None) -> int:
    if args:
        return reject_extra_args(CHECK_NAME, args)
    output.running("Judging every resolved dependency's licence against the policy…")
    policy_path = _policy_path()
    if not policy_path.is_file():
        return _cannot_run([f"No licence policy at `{policy_path}`. install.sh seeds it; `security.licences.policy` can point elsewhere."])
    policy = _read_policy(policy_path)
    if policy is None:
        return _cannot_run([f"`{policy_path}` carries neither `allow-licenses` nor `deny-licenses`, so there is nothing to judge against."])
    root = Path.cwd()
    packages, skipped, failures = _inventory(root, config.get_bool("security.licences.include_dev", False))
    if failures:
        return _cannot_run(failures)
    denied, unknown = _judge(packages, policy)
    per_ecosystem: dict[str, int] = {}
    for pkg in packages:
        per_ecosystem[pkg["ecosystem"]] = per_ecosystem.get(pkg["ecosystem"], 0) + 1
    result = {
        "policy": str(policy_path), "judged": len(packages), "per_ecosystem": per_ecosystem,
        "denied": denied, "unknown": unknown, "not_scanned": skipped,
    }
    _report.write_reports(REPORT_JSON, REPORT_MD, result, _build_md_report)
    for reason in skipped:
        output.info(reason)
    if not packages and not skipped:
        output.info("No package-lock.json, pyproject.toml or requirements.txt here, so there is nothing to inventory.")
    if unknown:
        output.info(f"{len(unknown)} package(s) state no SPDX licence; listed in the report, not failed")
    output.footer(REPORT_DIR, [REPORT_MD.name])
    if denied:
        output.error(f"{len(denied)} package(s) carry a licence outside `{policy_path}`: " + ", ".join(f"{p['name']} ({p['licence']})" for p in denied[:5]) + (" …" if len(denied) > 5 else ""))
        return 1
    output.success(f"Every one of {len(packages)} judged licence(s) is on the allowlist")
    return 0
