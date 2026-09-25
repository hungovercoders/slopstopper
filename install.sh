#!/usr/bin/env bash
# install.sh — installs the SlopStopper tooling into a target repository.
#
# Usage (from inside this repo):
#   ./install.sh [TARGET_DIR]
#
# Usage (recommended two-step from GitHub):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
#   bash install.sh [TARGET_DIR]
#
# Usage (one-liner from GitHub, review the script first):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
#
# When piped from curl the script clones a temporary copy of the repo and
# installs from there, so no local checkout is required.
#
# Layout installed (all SlopStopper-owned files are under the `ss` namespace):
#
#   slopstopper-cli             # installed via mise (pinned in mise.toml);
#                               #   every check runs via `slopstopper run ...`.
#   Taskfile.yml                # thin root; created on fresh installs, left
#                               #   alone if you already have one (instructions
#                               #   printed in that case)
#   Taskfile.ss.yml             # all SlopStopper task shims; always
#                               #   refreshed on re-run so updates flow through
#   .ss/.workflows-installed    # manifest of installed workflows (commit this)
#   .ss/.installed-from         # slopstopper commit this install came from (commit this)
#   .ss/reports/                # SlopStopper-owned scan/report output dirs
#                               # (every CLI-managed file — Playwright specs,
#                               # Playwright config, lighthouserc dev/prod,
#                               # server.js — lives in the slopstopper-cli
#                               # wheel. To customise, `slopstopper templates
#                               # eject <name>` writes the file into .ss/ and
#                               # the CLI's templates resolver prefers it.)
#   .github/workflows/ss-*      # all SlopStopper workflows are ss- prefixed
#                               #   so they group together in the Actions UI
#                               #   and cannot clash with your existing workflows
#   .githooks/pre-push          # runs the fast hygiene checks before every push
#                               #   (core.hooksPath → .githooks; skipped if you
#                               #   already run husky/lefthook/pre-commit)
#
# Workflow set ships in three conceptual layers:
#   1. Static analysis  — work on any code (SAST, Secrets, Trivy, complexity, doc checks)
#   2. Web-app dynamic  — need a URL (Smoke, Accessibility, CWV, DAST, SEO, Broken Links)
#   3. Agentic updater  — needs COPILOT_GITHUB_TOKEN (gh-aw doc-updater)
# Deploy is intentionally not a layer: connect your repo in the Cloudflare
# dash (Workers & Pages → Create → Connect to Git) and you get production
# deploys, PR previews and preview cleanup for free — no workflow needed.
# Don't use one of the layers? Delete its workflows from .github/workflows/.
# Re-running this installer will respect that deletion (it tracks what it
# installed in .ss/.workflows-installed).

set -euo pipefail

REPO_URL="https://github.com/hungovercoders/slopstopper.git"

# ── argument parsing ─────────────────────────────────────────────────────────
#
# Default mode ships Task-flavour workflows (every check is `task ss:<name>` —
# the canonical interface for humans, agents and CI alike). Adopters who'd
# rather skip Task in CI pass `--no-task` (or set SLOPSTOPPER_NO_TASK=1) and
# the workflows are post-processed at install time to call slopstopper-cli
# directly. See docs/architecture/ for the design rationale.

USE_TASK=true
if [ -n "${SLOPSTOPPER_NO_TASK:-}" ]; then
  USE_TASK=false
fi

INSTALL_SKILLS=true
if [ -n "${SLOPSTOPPER_NO_SKILLS:-}" ]; then
  INSTALL_SKILLS=false
fi

INSTALL_HOOKS=true
if [ -n "${SLOPSTOPPER_NO_HOOKS:-}" ]; then
  INSTALL_HOOKS=false
fi

# Project-shape profile. A profile is a preset for `workflows.disabled` —
# it switches off the checks a repo of that shape has no use for (an API
# has no Core Web Vitals; a library has no URL at all). The flag writes
# `profile:` into .slopstopper.yml so the choice survives re-runs and shows
# up in a diff, then the workflow set follows from the config — the same
# reasoning as workflows.disabled below. Empty = leave the config alone
# (an unset `profile:` means `ui`, i.e. today's full suite).
PROFILE_FLAG="${SLOPSTOPPER_PROFILE:-}"

# slopstopper-cli version control. The pinned version lives in the target's
# mise.toml ([tools] "pipx:slopstopper-cli"). A plain run honours that pin;
# these flags move it deliberately (both wrap `mise use`). CLI_VERSION_FLAG
# wins over UPGRADE_CLI if both given.
UPGRADE_CLI=false
CLI_VERSION_FLAG=""

POSITIONAL=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-task)
      USE_TASK=false
      shift
      ;;
    --no-skills)
      INSTALL_SKILLS=false
      shift
      ;;
    --no-hooks)
      INSTALL_HOOKS=false
      shift
      ;;
    --profile)
      PROFILE_FLAG="${2:-}"
      [ -n "$PROFILE_FLAG" ] || { echo "  ❌ --profile requires a name (e.g. --profile api)" >&2; exit 1; }
      shift 2
      ;;
    --profile=*)
      PROFILE_FLAG="${1#*=}"
      [ -n "$PROFILE_FLAG" ] || { echo "  ❌ --profile requires a name (e.g. --profile=api)" >&2; exit 1; }
      shift
      ;;
    --upgrade-cli)
      UPGRADE_CLI=true
      shift
      ;;
    --cli-version)
      CLI_VERSION_FLAG="${2:-}"
      [ -n "$CLI_VERSION_FLAG" ] || { echo "  ❌ --cli-version requires a version argument (e.g. --cli-version 1.2.3)" >&2; exit 1; }
      shift 2
      ;;
    --cli-version=*)
      CLI_VERSION_FLAG="${1#*=}"
      [ -n "$CLI_VERSION_FLAG" ] || { echo "  ❌ --cli-version requires a version argument (e.g. --cli-version=1.2.3)" >&2; exit 1; }
      shift
      ;;
    --help|-h)
      cat <<'USAGE'
install.sh — install the SlopStopper quality suite into a target repo.

Usage:
  bash install.sh [TARGET_DIR]                 # Task-driven workflows (default)
  bash install.sh --no-task [TARGET_DIR]       # CLI-driven workflows (no Task install)
  bash install.sh --no-skills [TARGET_DIR]     # Skip installing Claude Code skills
  bash install.sh --no-hooks [TARGET_DIR]      # Skip installing the pre-push hygiene hook
  bash install.sh --profile api [TARGET_DIR]   # Install the check set for a repo of that shape
  bash install.sh --upgrade-cli [TARGET_DIR]   # Bump the pinned CLI to the latest on PyPI
  bash install.sh --cli-version X.Y.Z [TARGET] # Pin the CLI to an exact version

Env var equivalents:
  SLOPSTOPPER_NO_TASK=1 bash install.sh
  SLOPSTOPPER_NO_SKILLS=1 bash install.sh
  SLOPSTOPPER_NO_HOOKS=1 bash install.sh
  SLOPSTOPPER_PROFILE=api bash install.sh

Profiles (--profile) tailor the suite to the repo's shape:

  ui       a site or app that serves HTML — every check applies (default)
  api      JSON/gRPC endpoints, no browser surface — drops the eight
           browser-and-SEO reliability checks, which assume HTML and a
           public web surface and would go red rather than no-op
  library  a library, CLI or package with no deployed surface — also drops
           DAST and CSP exceptions

The flag writes `profile:` into .slopstopper.yml, so the choice survives
re-runs and is visible in review; the workflow set is derived from that key
on every run. Omitting the flag leaves an existing `profile:` untouched and
prints a suggestion when the key is unset. To keep one check the profile
drops, list it under `workflows.enabled` in .slopstopper.yml. See
`slopstopper profile list` for the full mapping.

Default mode installs workflows that invoke `task ss:<check>` so the suite
shares a single invocation surface with the rest of your codebase. `--no-task`
installs workflows that invoke `slopstopper run <check>` directly.

The slopstopper-cli version is pinned per-repo in mise.toml ([tools]
"pipx:slopstopper-cli") and installed via mise, which activates it per-directory
so the active version follows the repo. A plain run installs that pinned version
and never moves it, so a breaking upstream release can't reach you unannounced.
First install pins to the latest published version; --upgrade-cli / --cli-version
move the pin later (both wrap `mise use`). mise is required — see
https://mise.jdx.dev. A legacy .slopstopper.yml cli_version pin is migrated into
mise.toml automatically on the next run.

The installer also writes the SlopStopper Claude Code skills into
<target>/.claude/skills/slopstopper-*/SKILL.md so every contributor on the
repo benefits from them on git clone (Claude Code auto-discovers project-
level skills). Pass --no-skills to skip this step. To refresh skills later
without re-running the whole installer, use install-skill.sh.

The installer also wires a pre-push git hook (.githooks/pre-push, via
core.hooksPath) that runs the fast static hygiene checks (task ss:hygiene:test)
before every push, so the first CI run confirms rather than discovers. It won't
touch an existing hook manager (husky / lefthook / pre-commit) or a custom
core.hooksPath — in that case it drops the hook file in and prints how to opt in.
Pass --no-hooks to skip. Bypass a single push with 'git push --no-verify'.
USAGE
      exit 0
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]:+${POSITIONAL[@]}}"

TARGET_DIR="${1:-$(pwd)}"

# ── helpers ──────────────────────────────────────────────────────────────────

info()    { echo "  ℹ  $*"; }
success() { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
error()   { echo "  ❌ $*" >&2; exit 1; }

sep() { echo "────────────────────────────────────────────────────────────"; }

# Latest slopstopper-cli version published on PyPI. Empty string on any
# failure (offline, no curl, malformed JSON) — callers treat empty as
# "unknown" and fall back to best-effort behaviour rather than blocking.
latest_pypi_version() {
  # Test seam (used by cli/tests/test_install.py alongside SKIP_CLI_INSTALL):
  # pin the "latest" answer so first-install/--upgrade-cli paths are
  # deterministic and offline. Not documented for adopters.
  if [ -n "${SLOPSTOPPER_FORCE_LATEST:-}" ]; then
    echo "$SLOPSTOPPER_FORCE_LATEST"
    return 0
  fi
  curl -fsSL "https://pypi.org/pypi/slopstopper-cli/json" 2>/dev/null \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["info"]["version"])' 2>/dev/null \
    || true
}

# Installed CLI version as a bare semver (e.g. "0.8.0"), or empty if the
# binary is absent. `slopstopper --version` prints "slopstopper <ver>".
installed_cli_version() {
  slopstopper --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true
}

# version_lt A B → exit 0 if A is strictly older than B (semver ordering).
version_lt() {
  [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" = "$1" ]
}

# Path to the target's mise config — the canonical pin lives here now. Prefer
# an existing file (so we never create a second config alongside an adopter's),
# else default to mise.toml. mise reads any of these names.
mise_config_path() {
  local f
  for f in mise.toml .mise.toml mise.local.toml .config/mise/config.toml; do
    [ -f "$TARGET_DIR/$f" ] && { echo "$TARGET_DIR/$f"; return 0; }
  done
  echo "$TARGET_DIR/mise.toml"
}

# Read the pinned slopstopper-cli version from a mise config (the
# `pipx:slopstopper-cli = "X.Y.Z"` entry under [tools]). Empty if absent. The
# ss-*.yml workflows resolve the same pin via `jdx/mise-action` reading this
# file, so install and CI agree without a TOML library.
read_mise_cli_version() {
  [ -f "$1" ] || return 0
  sed -n 's/.*pipx:slopstopper-cli"\{0,1\}[[:space:]]*=[[:space:]]*"\([0-9][0-9.]*\)".*/\1/p' "$1" | head -1
}

# Legacy parse: the pre-mise pin lived in .slopstopper.yml (cli_version:). Read
# it so a refresh can migrate the value into mise.toml, then strip the key.
read_legacy_cli_version() {
  [ -f "$1" ] || return 0
  sed -n 's/^cli_version:[[:space:]]*["'\'']\{0,1\}\([0-9][0-9.]*\).*/\1/p' "$1" | head -1
}

# Migration cleanup: remove the now-defunct cli_version key (and its preceding
# comment block, if present) from .slopstopper.yml. `-i.bak` + rm keeps this
# portable across BSD (macOS) and GNU sed.
strip_legacy_cli_version() {
  local cfg="$1"
  [ -f "$cfg" ] || return 0
  grep -qE '^cli_version:' "$cfg" 2>/dev/null || return 0
  awk '
    /^# ── slopstopper-cli version pin/ { skip=1 }
    skip && /^cli_version:/             { skip=0; next }
    skip                                { next }
    /^cli_version:/                     { next }
    { print }
  ' "$cfg" > "$cfg.tmp" && mv "$cfg.tmp" "$cfg"
}

# Migration cleanup: remove the dead node_version key (and its preceding comment
# block, if present) from .slopstopper.yml. The key was never read (CI used the
# SLOPSTOPPER_NODE_VERSION repo variable); node lives in mise.toml ([tools] node)
# now, so the key is simply removed — there's no value worth migrating.
strip_legacy_node_version() {
  local cfg="$1"
  [ -f "$cfg" ] || return 0
  grep -qE '^node_version:' "$cfg" 2>/dev/null || return 0
  awk '
    /^# ── Node version pin/ { skip=1 }
    skip && /^node_version:/  { skip=0; next }
    skip                      { next }
    /^node_version:/          { next }
    { print }
  ' "$cfg" > "$cfg.tmp" && mv "$cfg.tmp" "$cfg"
}

# Set a [tools] entry in a mise config, portable across BSD/GNU and offline
# (no mise binary needed — used by the SKIP_CLI_INSTALL test seam). Real
# installs go through `mise use` instead, which also installs the tool.
# Creates the file and [tools] section if absent; replaces the entry if present.
write_mise_tool() {
  local cfg="$1" key="$2" ver="$3"
  local line="\"$key\" = \"$ver\""
  local pat="^[[:space:]]*\"?${key}\"?[[:space:]]*="
  if [ ! -f "$cfg" ]; then
    mkdir -p "$(dirname "$cfg")"
    printf '[tools]\n%s\n' "$line" > "$cfg"
  elif grep -qE "$pat" "$cfg" 2>/dev/null; then
    awk -v pat="$pat" -v repl="$line" '$0 ~ pat {print repl; next} {print}' \
      "$cfg" > "$cfg.tmp" && mv "$cfg.tmp" "$cfg"
  elif grep -qE '^\[tools\]' "$cfg" 2>/dev/null; then
    awk -v repl="$line" '{print} /^\[tools\]/ && !d {print repl; d=1}' \
      "$cfg" > "$cfg.tmp" && mv "$cfg.tmp" "$cfg"
  else
    printf '\n[tools]\n%s\n' "$line" >> "$cfg"
  fi
}

# Default Node version slopstopper seeds into a fresh adopter mise config. Node is
# a tool version, so it belongs in mise (not .slopstopper.yml); the ss-*.yml
# workflows get it from this pin via jdx/mise-action — no setup-node step.
DEFAULT_NODE_VERSION="20"

# True if the target already declares a Node version somewhere mise (and the
# workflows) honour — a `node` [tools] entry in the mise config, or a
# .node-version / .nvmrc file. We seed our own node pin only when none of these
# exist, so a re-run never clobbers an adopter's existing Node setup.
target_has_node_pin() {
  local mcfg="$1"
  [ -f "$TARGET_DIR/.node-version" ] && return 0
  [ -f "$TARGET_DIR/.nvmrc" ] && return 0
  [ -f "$mcfg" ] && grep -qE '^[[:space:]]*"?node"?[[:space:]]*=' "$mcfg" 2>/dev/null && return 0
  return 1
}

# slopstopper-cli version active in the target per mise (independent of whether
# mise is activated in this shell). Empty if mise can't resolve it.
mise_active_cli_version() {
  ( cd "$TARGET_DIR" 2>/dev/null && mise exec -- slopstopper --version 2>/dev/null ) \
    | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true
}

# ── prerequisite check ────────────────────────────────────────────────────────
#
# Surface missing tools up front rather than letting the install fail mid-flight
# with a cryptic "command not found". `git` is hard-required (the installer
# clones this repo); the rest are soft-required (you'll need them to actually
# run any check, but the install itself will succeed without them).

preflight() {
  local missing_hard=()
  local missing_soft=()

  command -v git     >/dev/null 2>&1 || missing_hard+=("git")
  command -v python3 >/dev/null 2>&1 || missing_hard+=("python3 (slopstopper-cli is a Python package): https://www.python.org/downloads/")
  # mise is the canonical toolchain manager now — it installs the pinned
  # slopstopper-cli (and task) from mise.toml and activates them per-directory,
  # so the version follows the repo instead of a single global binary. Skip the
  # hard requirement under the SKIP_CLI_INSTALL test seam (no real install).
  if [ "${SKIP_CLI_INSTALL:-0}" != "1" ]; then
    command -v mise >/dev/null 2>&1 || missing_hard+=("mise (installs the pinned slopstopper-cli + task): https://mise.jdx.dev")
  fi
  command -v node    >/dev/null 2>&1 || missing_soft+=("node (Playwright, Lighthouse CI, markdownlint, TypeScript): https://nodejs.org/")
  command -v docker  >/dev/null 2>&1 || info "Docker not found — only needed for DAST. Skipping check."

  if [ "${#missing_hard[@]}" -gt 0 ]; then
    for tool in "${missing_hard[@]}"; do
      echo "  ❌ Required tool missing: $tool" >&2
    done
    error "Install the tools above and re-run."
  fi

  if [ "${#missing_soft[@]}" -gt 0 ]; then
    warn "The following tools aren't installed — you'll need them to run the checks SlopStopper installs:"
    for tool in "${missing_soft[@]}"; do
      echo "      • $tool"
    done
    info "Continuing with install; install the tools above before running any task."
  fi
}

preflight

# ── locate source directory ───────────────────────────────────────────────────

# Resolve the directory that contains this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)" || true

# Resolve the absolute target so we can compare against SCRIPT_DIR. If they
# are the same directory, the user is running install.sh from inside an
# adopter repo and we MUST clone — otherwise the cp Taskfile.ss.yml step
# would copy the existing Taskfile.ss.yml to itself, never picking up
# upstream changes. Using Taskfile.ss.yml as the slopstopper-source marker
# (the previous behaviour) failed exactly this case because the adopter has
# their own Taskfile.ss.yml from a prior install.
TARGET_ABS="$(cd "$TARGET_DIR" 2>/dev/null && pwd || echo "$TARGET_DIR")"

# Decide whether SCRIPT_DIR is the genuine slopstopper repo. Markers:
#  - templates/  (only slopstopper has it; adopters get the templates
#    expanded into .slopstopper.yml, public/_headers, etc.)
#  - install.sh  (this script itself, sanity check)
#  - SCRIPT_DIR != TARGET_ABS (running install.sh from inside a target
#    that happens to ship its own templates/ dir would still trigger this).
SCRIPT_IS_SOURCE=0
if [ -n "$SCRIPT_DIR" ] \
   && [ -d "$SCRIPT_DIR/templates" ] \
   && [ -f "$SCRIPT_DIR/install.sh" ] \
   && [ "$SCRIPT_DIR" != "$TARGET_ABS" ]; then
  SCRIPT_IS_SOURCE=1
fi

if [ "$SCRIPT_IS_SOURCE" -eq 0 ]; then
  if ! command -v git &>/dev/null; then
    error "git is required when running install.sh from outside the SlopStopper repo. Please install git and try again."
  fi

  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  info "Cloning template repository into a temporary directory…"
  git clone --depth=1 "$REPO_URL" "$TMP_DIR/template" &>/dev/null \
    || error "Failed to clone $REPO_URL"

  SCRIPT_DIR="$TMP_DIR/template"
fi

# ── validate target ───────────────────────────────────────────────────────────

[ -d "$TARGET_DIR" ] || error "Target directory does not exist: $TARGET_DIR"

sep
echo "  🛠  SlopStopper — installing tooling"
echo "  Source : $SCRIPT_DIR"
echo "  Target : $TARGET_DIR"
sep

# ── project-shape profile helpers ────────────────────────────────────────────
#
# A profile is a preset for `workflows.disabled`: it names the workflows a
# repo of that shape has no use for (an API has no Core Web Vitals; a
# library has no URL at all). The mapping lives in
# cli/slopstopper/data/profiles.json and is read here through the CLI's own
# slopstopper.profiles module, imported straight from the source tree
# ($SCRIPT_DIR/cli) rather than from an installed wheel.
#
# That matters: the installer must be able to resolve the workflow set
# before (and independently of) the mise/CLI install step succeeding, and
# there must be exactly one implementation of "which workflows does this
# repo carry" shared by the installer and the CLI. python3 is a hard
# prereq (see preflight) and $SCRIPT_DIR is always a slopstopper checkout
# by this point, so both hold.

ss_profiles_py() {
  # Run a python snippet with slopstopper importable and CWD = the target
  # repo, because slopstopper.config reads .slopstopper.yml from CWD.
  # Extra args are passed through as sys.argv[1:].
  local snippet="$1"
  shift
  ( cd "$TARGET_DIR" && PYTHONPATH="$SCRIPT_DIR/cli" python3 -c "$snippet" "$@" )
}

profile_names() {
  ss_profiles_py 'from slopstopper import profiles; print(" ".join(profiles.names()))'
}

profile_is_valid() {
  ss_profiles_py '
import sys
from slopstopper import profiles
sys.exit(0 if profiles.describe(sys.argv[1]) else 1)
' "$1" >/dev/null 2>&1
}

profile_active() {
  ss_profiles_py 'from slopstopper import profiles; print(profiles.active_name())'
}

profile_summary() {
  ss_profiles_py '
from slopstopper import profiles
entry = profiles.describe(profiles.active_name()) or {}
print(entry.get("summary", ""))
'
}

# Newline-separated workflow filenames this repo should not carry:
# the profile's set minus workflows.enabled, plus workflows.disabled.
profile_effective_disabled() {
  ss_profiles_py '
from slopstopper import profiles
for name in sorted(profiles.effective_disabled()):
    print(name)
'
}

# Advisory shape detection: prints "<profile>\t<reason>". Never applied
# automatically — a curl-piped install is non-interactive, and silently
# switching checks off is worse than the default superset going red.
profile_detect() {
  ss_profiles_py '
from slopstopper import profiles
name, reason = profiles.detect()
print(name + "\t" + reason)
'
}

# Write `profile: <name>` into the target .slopstopper.yml — replacing an
# existing top-level key in place, or appending a documented block if the
# file predates the key. Comment-preserving line edit, same spirit as the
# legacy cli_version migration above.
write_profile_key() {
  local name="$1"
  ss_profiles_py '
import sys
from pathlib import Path

name = sys.argv[1]
path = Path(".slopstopper.yml")
if not path.is_file():
    sys.exit(0)

lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith("profile:"):
        if line.strip() == f"profile: {name}":
            print("unchanged")
            sys.exit(0)
        lines[i] = f"profile: {name}\n"
        path.write_text("".join(lines), encoding="utf-8")
        print("replaced")
        sys.exit(0)

block = (
    "\n# \u2500\u2500 Project-shape profile \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "# Which checks apply to a repo of this shape. See\n"
    "# `slopstopper profile list` for the full mapping.\n"
    f"profile: {name}\n"
)
with path.open("a", encoding="utf-8") as fh:
    fh.write(block)
print("appended")
' "$name"
}

if [ -n "$PROFILE_FLAG" ]; then
  if ! profile_is_valid "$PROFILE_FLAG"; then
    error "Unknown --profile '$PROFILE_FLAG'. Expected one of: $(profile_names)"
  fi
fi

# ── install files ─────────────────────────────────────────────────────────────

# 1. Taskfile.ss.yml — always refreshed (SlopStopper-owned, safe to overwrite).
cp "$SCRIPT_DIR/Taskfile.ss.yml" "$TARGET_DIR/Taskfile.ss.yml"
success "Taskfile.ss.yml installed (refreshed)"

# 2. Root Taskfile.yml — only create if missing.
# If the consumer already has one, print clear instructions instead of editing it.
if [ -f "$TARGET_DIR/Taskfile.yml" ]; then
  if grep -qE "^[[:space:]]+ss:[[:space:]]*$" "$TARGET_DIR/Taskfile.yml" 2>/dev/null \
     || grep -q "Taskfile.ss.yml" "$TARGET_DIR/Taskfile.yml" 2>/dev/null; then
    info "Taskfile.yml already references Taskfile.ss.yml — no changes needed"
  else
    warn "Taskfile.yml already exists — leaving it alone."
    echo ""
    echo "  Add the following block to your existing Taskfile.yml so the"
    echo "  SlopStopper tasks become available as 'task ss:<name>':"
    echo ""
    echo "    includes:"
    echo "      ss:"
    echo "        taskfile: ./Taskfile.ss.yml"
    echo ""
  fi
else
  # Write a minimal root Taskfile inline rather than copying slopstopper's
  # own — slopstopper's root file carries `contributing:*` + `decisions:*`
  # tasks that are scoped to working on slopstopper itself, not the suite
  # being shipped to adopters.
  cat > "$TARGET_DIR/Taskfile.yml" <<'YAML'
version: '3'

includes:
  ss:
    taskfile: ./Taskfile.ss.yml
YAML
  success "Taskfile.yml installed"
fi

# 3. slopstopper-cli — pinned and installed via mise. The canonical pin lives
#    in the target's mise.toml ([tools] "pipx:slopstopper-cli"). mise installs
#    it (and `task`) and activates them per-directory, so the active version
#    follows the repo — no single global binary to drift between repos. A
#    breaking upstream release never lands until you move the pin
#    (--upgrade-cli / --cli-version, both wrappers over `mise use`).
#
# If an `.ss/` overlay (specs, playwright config, lighthouse config) is
# already present in the target, the CLI's templates module prefers
# those files over the package data — same shape as the workflows.
#
# .slopstopper.yml is seeded from templates/slopstopper.yml.starter — the
# handful of keys most repos set, with a pointer to the full schema
# reference (.slopstopper.yml.example) for everything else. The schema
# reference used to be copied verbatim, so an adopter's first config was
# the whole schema rather than the few keys they set. A legacy cli_version
# is migrated into mise.toml and stripped below.
if [ ! -f "$TARGET_DIR/.slopstopper.yml" ] && [ -f "$SCRIPT_DIR/templates/slopstopper.yml.starter" ]; then
  cp "$SCRIPT_DIR/templates/slopstopper.yml.starter" "$TARGET_DIR/.slopstopper.yml"
  success ".slopstopper.yml: seeded $TARGET_DIR/.slopstopper.yml (a starter — every other key: https://github.com/hungovercoders/slopstopper/blob/main/.slopstopper.yml.example)"
fi

# Apply --profile / SLOPSTOPPER_PROFILE by writing the key into the
# (possibly just-seeded) config. The config is the home for this choice,
# not the flag: it has to survive a re-run and be visible in review, and
# the workflow set below is derived from the key rather than the flag.
# Without the flag an existing `profile:` is left exactly as it is.
if [ -n "$PROFILE_FLAG" ]; then
  case "$(write_profile_key "$PROFILE_FLAG")" in
    unchanged) info ".slopstopper.yml: profile already '$PROFILE_FLAG'" ;;
    replaced)  success ".slopstopper.yml: profile set to '$PROFILE_FLAG'" ;;
    appended)  success ".slopstopper.yml: profile '$PROFILE_FLAG' added" ;;
    *)         warn ".slopstopper.yml: no config file in target — profile '$PROFILE_FLAG' not written" ;;
  esac
fi

# Decide which version to pin:
#   --cli-version X.Y.Z  → that exact version
#   --upgrade-cli        → the latest on PyPI
#   mise pin already set → honour it (a plain refresh never moves the pin)
#   legacy cli_version   → migrate it (first move off the old mechanism)
#   nothing yet          → latest on PyPI (first install records it)
resolve_pinned_version() {
  local existing legacy
  existing="$(read_mise_cli_version "$(mise_config_path)")"
  legacy="$(read_legacy_cli_version "$TARGET_DIR/.slopstopper.yml")"
  if [ -n "$CLI_VERSION_FLAG" ]; then
    echo "$CLI_VERSION_FLAG"
  elif [ "$UPGRADE_CLI" = "true" ]; then
    latest_pypi_version
  elif [ -n "$existing" ]; then
    echo "$existing"
  elif [ -n "$legacy" ]; then
    echo "$legacy"
  else
    latest_pypi_version
  fi
}

sync_mise_cli() {
  local cfg="$TARGET_DIR/.slopstopper.yml"
  local mcfg pre_version pinned
  mcfg="$(mise_config_path)"
  pre_version="$(installed_cli_version)"
  pinned="$(resolve_pinned_version)"

  # Migrate off the old mechanism: drop the now-defunct cli_version key (its
  # value, if any, was already folded into `pinned` by resolve_pinned_version)
  # and the dead node_version key (never read — node lives in mise.toml now).
  strip_legacy_cli_version "$cfg"
  strip_legacy_node_version "$cfg"

  # Escape hatch for cli/tests/test_install.py: write the pin into mise.toml
  # offline (no mise binary, no PyPI) so tests can assert on it deterministically.
  if [ "${SKIP_CLI_INSTALL:-0}" = "1" ]; then
    [ -n "$pinned" ] && write_mise_tool "$mcfg" "pipx:slopstopper-cli" "$pinned"
    write_mise_tool "$mcfg" "task" "3"
    target_has_node_pin "$mcfg" || write_mise_tool "$mcfg" "node" "$DEFAULT_NODE_VERSION"
    info "Skipping mise install (SKIP_CLI_INSTALL=1)"
    SLOPSTOPPER_CLI_VERSION="$pinned"
    SLOPSTOPPER_CLI_PREVIOUS="$pre_version"
    return 0
  fi

  # `mise use` edits mise.toml AND installs the tool in one idempotent step —
  # it handles a moved pin (upgrade or downgrade) deterministically. Pin `task`
  # too so mise provides the canonical interface (no separate setup-task). Seed
  # `node` only when the adopter hasn't already declared one (mise.toml /
  # .node-version / .nvmrc), so we never override their build's Node version.
  local node_arg=""
  target_has_node_pin "$mcfg" || node_arg="node@$DEFAULT_NODE_VERSION"
  if [ -n "$pinned" ]; then
    info "Pinning slopstopper-cli@$pinned (+ task) in $(basename "$mcfg") via mise…"
    mise use --path "$mcfg" "pipx:slopstopper-cli@$pinned" "task@3" $node_arg >/dev/null \
      || error "mise use failed. Check the version exists on PyPI and your network, then retry."
  else
    warn "Could not determine a slopstopper-cli version (offline?). Pinning task only — set the CLI pin later with 'install.sh --upgrade-cli'."
    mise use --path "$mcfg" "task@3" $node_arg >/dev/null || true
  fi

  # mise installs into its own dir; the binary is only on PATH if mise is
  # activated in this shell, which it may not be. Validate via `mise exec`
  # within the target so the check is activation-independent.
  if ! ( cd "$TARGET_DIR" 2>/dev/null && mise which slopstopper >/dev/null 2>&1 ); then
    error "mise installed slopstopper-cli but can't resolve the 'slopstopper' binary. Ensure mise is set up and activated: https://mise.jdx.dev/getting-started.html"
  fi

  local post_version
  post_version="$(mise_active_cli_version)"

  # The active version must match the pin we asked for. A mismatch means the
  # pinned version doesn't exist on PyPI or a mirror served stale data — fail
  # loudly rather than limp on the wrong version.
  if [ -n "$pinned" ] && [ -n "$post_version" ] && [ "$post_version" != "$pinned" ]; then
    error "Asked for slopstopper-cli@$pinned but $post_version is active. Verify the version exists on PyPI, then run 'mise install' in $TARGET_DIR."
  fi

  success "slopstopper-cli installed ($post_version, pinned in $(basename "$mcfg"))"

  # Stash facts for the completion banner. LATEST is informational now — a
  # pin behind latest is a deliberate choice, not a fault.
  SLOPSTOPPER_CLI_VERSION="$post_version"
  SLOPSTOPPER_CLI_LATEST="$(latest_pypi_version)"
  SLOPSTOPPER_CLI_PREVIOUS="$pre_version"
}

sync_mise_cli


# 4. .ss/ overlay — nothing is seeded by default. Every CLI-managed
#    file (Playwright specs, Playwright config, lighthouserc dev/prod,
#    server.js) lives inside slopstopper-cli and is resolved at runtime
#    via .ss/ override → package-data fallback. Adopters who want to
#    customise a file run `slopstopper templates eject <name>` to copy
#    the bundled version into .ss/<name>.
mkdir -p "$TARGET_DIR/.ss"

# Clean up any legacy .ss/scripts/ left over from pre-CLI installs —
# every script previously copied into adopter repos is now bundled in
# slopstopper-cli (or was a slopstopper.dev-internal helper that didn't
# belong in adopter repos).
if [ -d "$TARGET_DIR/.ss/scripts" ]; then
  rm -rf "$TARGET_DIR/.ss/scripts"
  success ".ss/scripts/ removed (logic now lives in slopstopper-cli)"
fi

# Clean up legacy byte-equal template copies from pre-lift installs.
# If an adopter has customised any of these, leave the file alone — the
# CLI's templates resolver will keep using the .ss/ override.
# Detection: compare bytes against the package data shipped in the wheel
# the adopter just installed.
DATA_DIR="$(python3 -c 'import slopstopper, pathlib; print(pathlib.Path(slopstopper.__file__).resolve().parent / "data")' 2>/dev/null || true)"
if [ -n "$DATA_DIR" ] && [ -d "$DATA_DIR" ]; then
  scrub_if_byte_equal() {
    local rel="$1"
    local adopter="$TARGET_DIR/.ss/$rel"
    local pkg="$DATA_DIR/$rel"
    if [ -e "$adopter" ] && [ -e "$pkg" ] && cmp -s "$adopter" "$pkg"; then
      rm -rf "$adopter"
      success ".ss/$rel removed (unmodified copy of package-data fallback)"
    fi
  }
  scrub_if_byte_equal "playwright.config.js"
  scrub_if_byte_equal "lighthouserc.json"
  scrub_if_byte_equal "lighthouserc.prod.json"
  scrub_if_byte_equal "server.js"
  if [ -d "$TARGET_DIR/.ss/tests" ] && [ -d "$DATA_DIR/tests" ]; then
    if diff -rq "$TARGET_DIR/.ss/tests" "$DATA_DIR/tests" >/dev/null 2>&1; then
      rm -rf "$TARGET_DIR/.ss/tests"
      success ".ss/tests/ removed (unmodified copy of package-data fallback)"
    fi
  fi
fi

# 4. .github/workflows/ — install ss- prefixed generic workflows.
WORKFLOWS_SRC="$SCRIPT_DIR/.github/workflows"
WORKFLOWS_DST="$TARGET_DIR/.github/workflows"
mkdir -p "$WORKFLOWS_DST"

# Every workflow ships by default. The four layers are documented in
# the post-install matrix; consumers can delete any they don't want and
# re-running the installer will respect that deletion (tracked via
# .ss/.workflows-installed).
#
# copilot-setup-steps.yml is platform-fixed and not included here — install
# it manually if you use GitHub Copilot's setup-steps feature.
GENERIC_WORKFLOWS=(
  # Layer 1 — static analysis (works on any code)
  "ss-hygiene-complexity-check.yml"
  "ss-hygiene-csp-exceptions-check.yml"
  "ss-hygiene-docs-accuracy-check.yml"
  "ss-hygiene-docs-size-check.yml"
  "ss-hygiene-docs-structure-check.yml"
  "ss-hygiene-entry-files-check.yml"
  "ss-hygiene-auto-label-pr.yml"
  "ss-security-sast-check.yml"
  "ss-security-secrets-check.yml"
  "ss-security-vulnerability-all-check.yml"
  "ss-security-vulnerability-new-check.yml"
  "ss-workflow-failure-issue.yml"
  "ss-pr-summary.yml"
  # Layer 2 — web-app dynamic (need a URL)
  "ss-security-dast-check.yml"
  "ss-reliability-smoke-tests.yml"
  "ss-reliability-accessibility-check.yml"
  "ss-reliability-broken-links-check.yml"
  "ss-reliability-core-web-vitals.yml"
  "ss-reliability-seo-check.yml"
  "ss-reliability-llms-txt-check.yml"
  "ss-reliability-robots-txt-check.yml"
  "ss-reliability-sitemap-check.yml"
  "ss-reliability-api-health-check.yml"
  "ss-reliability-api-latency-check.yml"
  "ss-security-api-headers-check.yml"
  # The one hygiene check that needs a URL: drift means the spec measured
  # against the thing it documents, so it lives in layer 2 with the rest.
  "ss-hygiene-openapi-check.yml"
  # Layer 3 — agentic doc-updater (needs ANTHROPIC_API_KEY)
  # NB: gh-aw workflows ship as a .md source + .lock.yml compiled artifact.
  "ss-hygiene-doc-updater.md"
  "ss-hygiene-doc-updater.lock.yml"
)

MARKER_FILE="$TARGET_DIR/.ss/.workflows-installed"

# Workflows this repo shouldn't carry: the `profile:` preset minus
# workflows.enabled, plus workflows.disabled. Resolved once here and
# honoured both in the install loop below (skip, and remove a copy an
# earlier profile left behind) and in the sweep further down (which also
# catches names outside GENERIC_WORKFLOWS).
PROFILE_ACTIVE="$(profile_active)" || true
DISABLED_WORKFLOWS="$(profile_effective_disabled)" || true

# Degrade safely — and never silently. If the profiles module couldn't be
# resolved (no python3, unreadable cli/ tree), an empty name must not look
# like "this repo carries fewer checks" — but the full `ui` set must not
# land in a repo whose config explicitly opted out of it either. So: a
# non-default `profile:` aborts here (no workflows have been written yet);
# the default warns and continues.
if [ -z "$PROFILE_ACTIVE" ]; then
  CONFIGURED_PROFILE="$(sed -n "s/^profile:[[:space:]]*[\"']\{0,1\}\([A-Za-z0-9_-]*\).*/\1/p" "$TARGET_DIR/.slopstopper.yml" 2>/dev/null | head -n 1)"
  if [ -n "$CONFIGURED_PROFILE" ] && [ "$CONFIGURED_PROFILE" != "ui" ]; then
    error "could not resolve the workflow set for profile '$CONFIGURED_PROFILE' (python3 or the slopstopper.profiles module is unavailable). Refusing to install the full 'ui' set into a repo that opted out of it — fix the toolchain and re-run; no workflows were written."
  fi
  warn "profile lookup failed (python3 or slopstopper.profiles unavailable) — defaulting to 'ui', so every check installs. Re-run once the toolchain works if that is not what you want."
  PROFILE_ACTIVE="ui"
fi

workflow_is_disabled() {
  [ -n "$DISABLED_WORKFLOWS" ] && printf '%s\n' "$DISABLED_WORKFLOWS" | grep -Fxq "$1"
}

# Load the set of workflows we installed last time (if any). If a workflow
# is in this list AND missing from the consumer's repo now, they deleted it
# and we won't re-add it. Compatible with bash 3.2 (no associative arrays).
was_previously_installed() {
  [ "$IGNORE_STALE_MARKER" -eq 1 ] && return 1
  [ -f "$MARKER_FILE" ] && grep -Fxq "$1" "$MARKER_FILE"
}

# Stale-marker detection: a marker lists every workflow as previously-
# installed but zero `ss-*.yml` files exist on disk. The only realistic
# explanation is the marker was left over from a prior branch (e.g. a
# revert) and the deletion-respect logic would now skip every workflow,
# yielding a silent zero-workflows install. A real user would not delete
# every workflow; treat this as a stale marker and re-install fresh.
#
# Use `find` rather than `ls` for the count — `ls path/glob*` returns
# non-zero when the glob has no matches, which combines with `set -e -o
# pipefail` to abort the script. `find` returns 0 even on no matches.
IGNORE_STALE_MARKER=0
if [ -f "$MARKER_FILE" ]; then
  on_disk_count=$(find "$WORKFLOWS_DST" -maxdepth 1 -name 'ss-*.yml' -type f 2>/dev/null | wc -l | tr -d ' ')
  marker_count=$(grep -c '^ss-' "$MARKER_FILE" 2>/dev/null || true)
  [ -z "$marker_count" ] && marker_count=0
  if [ "$on_disk_count" = "0" ] && [ "$marker_count" -gt 0 ]; then
    IGNORE_STALE_MARKER=1
    warn "Stale .ss/.workflows-installed detected ($marker_count entries, 0 workflows on disk) — treating as a fresh install and re-adding all workflows. If you genuinely deleted every workflow, set workflows.disabled in .slopstopper.yml instead so the choice survives re-runs."
  fi
fi

INSTALLED_WORKFLOWS=0
REFRESHED_WORKFLOWS=0
DELETED_RESPECTED=0
PROFILE_SKIPPED=0
PROFILE_REMOVED=0
NEW_MARKER_CONTENT=""

for wf in "${GENERIC_WORKFLOWS[@]}"; do
  SRC="$WORKFLOWS_SRC/$wf"
  DST="$WORKFLOWS_DST/$wf"
  [ -f "$SRC" ] || continue

  # Profile / config says this repo doesn't carry this workflow. Remove a
  # copy an earlier install left behind (so switching ui → api cleans up),
  # and deliberately keep it out of the marker: the marker means "we
  # installed this", so omitting it lets a later profile change bring the
  # workflow back instead of the deletion-respect rule below suppressing it.
  if workflow_is_disabled "$wf"; then
    if [ -f "$DST" ]; then
      rm -f "$DST"
      (( PROFILE_REMOVED++ )) || true
    fi
    (( PROFILE_SKIPPED++ )) || true
    continue
  fi

  # Respect deletions: if we installed it before AND it's gone now, leave it gone.
  if was_previously_installed "$wf" && [ ! -f "$DST" ]; then
    (( DELETED_RESPECTED++ )) || true
    continue
  fi

  if [ -f "$DST" ]; then
    cp "$SRC" "$DST"
    (( REFRESHED_WORKFLOWS++ )) || true
  else
    cp "$SRC" "$DST"
    (( INSTALLED_WORKFLOWS++ )) || true
  fi
  NEW_MARKER_CONTENT+="$wf"$'\n'
done

# Write the updated marker (atomic via tmp + mv).
printf '%s' "$NEW_MARKER_CONTENT" > "$MARKER_FILE.tmp" && mv "$MARKER_FILE.tmp" "$MARKER_FILE"

# Record the slopstopper commit this install came from. Everything above —
# workflows, Taskfile.ss.yml, the config schema those read — is that
# commit's, so a refresh can diff upstream between the committed value and
# the new one (the slopstopper-install skill's "Spot newly-shipped knobs").
# Skipped when the source isn't a git checkout.
if [ -e "$SCRIPT_DIR/.git" ]; then
  SOURCE_SHA="$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || true)"
  [ -n "$SOURCE_SHA" ] && printf '%s\n' "$SOURCE_SHA" > "$TARGET_DIR/.ss/.installed-from"
fi

success "$INSTALLED_WORKFLOWS workflow(s) installed, $REFRESHED_WORKFLOWS refreshed, $DELETED_RESPECTED previously-deleted skipped"

if [ "$PROFILE_SKIPPED" -gt 0 ]; then
  info "profile '$PROFILE_ACTIVE': $PROFILE_SKIPPED workflow(s) not installed for this repo shape ($PROFILE_REMOVED removed from a previous install)"
  info "  see 'slopstopper profile show'; list one under workflows.enabled in .slopstopper.yml to keep it"
fi

# Post-process workflows for --no-task mode: rewrite `task ss:<X> -- args` into
# `slopstopper run <X> args`. The CLI accepts the same bare-positional URL
# adopters' shims pass through, so the resulting workflows are functionally
# identical — just without any `task ss:*` invocation. The toolchain step
# (jdx/mise-action) is unchanged: it still installs the pinned slopstopper-cli
# from mise.toml (mise also installs `task`, which simply goes unused here).
#
# Idempotent: re-running install.sh without --no-task re-copies the
# Task-flavour workflow from source on top, so adopters can switch modes
# by re-running with/without the flag.
if [ "$USE_TASK" = "false" ]; then
  python3 - "$WORKFLOWS_DST" <<'PY'
import re
import sys
from pathlib import Path

workflows_dst = Path(sys.argv[1])

# Order matters: handle the `-- ` separator form first, then bare invocations.
# Shim names match CLI check names one-to-one — no alias mapping needed.
# `task -x` (pass the command's exit code through instead of Task's 201)
# is matched too; the CLI returns the check's own code natively.
invoke_with_args = re.compile(r"task (?:-x )?ss:([a-z][a-z0-9_:-]+) -- ")
invoke_bare      = re.compile(r"task (?:-x )?ss:([a-z][a-z0-9_:-]+)")

transformed = 0
for path in sorted(workflows_dst.glob("ss-*.yml")):
    text = path.read_text()
    original = text
    text = invoke_with_args.sub(r"slopstopper run \1 ", text)
    text = invoke_bare.sub(r"slopstopper run \1", text)
    if text != original:
        path.write_text(text)
        transformed += 1

print(f"  ✅ Post-processed {transformed} workflow(s) for --no-task mode (invocations rewritten to slopstopper-cli)")
PY
fi

# 5. Merge devDependencies into package.json if one exists.
PKG="$TARGET_DIR/package.json"
SRC_PKG="$SCRIPT_DIR/package.json"
if [ -f "$PKG" ] && command -v node &>/dev/null; then
  _TMP_MERGE="$(mktemp)"
  _TMP_ADDED="$(mktemp)"
  node - "$PKG" "$SRC_PKG" "$_TMP_ADDED" >"$_TMP_MERGE" <<'JS' || true
const fs = require('fs');
const [, , dst, src, addedFile] = process.argv;
const d = JSON.parse(fs.readFileSync(dst, 'utf8'));
const s = JSON.parse(fs.readFileSync(src, 'utf8'));
const added = [];
const conflicts = [];
d.devDependencies = d.devDependencies || {};
for (const [k, v] of Object.entries(s.devDependencies || {})) {
  if (!d.devDependencies[k]) { d.devDependencies[k] = v; added.push(k); }
  else if (d.devDependencies[k] !== v) { conflicts.push(`${k}: existing=${d.devDependencies[k]} template=${v}`); }
}
process.stdout.write(JSON.stringify(d, null, 2) + '\n');
fs.writeFileSync(addedFile, JSON.stringify({ added, conflicts }));
JS
  MERGED="$(cat "$_TMP_MERGE" 2>/dev/null || true)"
  rm -f "$_TMP_MERGE"
  if [ -n "$MERGED" ]; then
    echo "$MERGED" > "$PKG"
    if [ -f "$_TMP_ADDED" ]; then
      ADDED_PKGS="$(node -pe "JSON.parse(require('fs').readFileSync('$_TMP_ADDED','utf8')).added.join(', ')" 2>/dev/null || true)"
      CONFLICT_PKGS="$(node -pe "JSON.parse(require('fs').readFileSync('$_TMP_ADDED','utf8')).conflicts.join('; ')" 2>/dev/null || true)"
      rm -f "$_TMP_ADDED"
      if [ -n "$ADDED_PKGS" ]; then
        success "Added devDependencies: $ADDED_PKGS"
      else
        info "No new devDependencies to add"
      fi
      if [ -n "$CONFLICT_PKGS" ]; then
        warn "Version conflicts (your version kept): $CONFLICT_PKGS"
      fi
    fi
  fi
elif [ ! -f "$PKG" ]; then
  cp "$SRC_PKG" "$PKG"
  success "package.json installed"
fi

# 6. Seed adopter-default templates. seed_template() copies <src> to <dst>
# only if <dst> does not exist; never overwrites. The whole point is to
# remove the cliff between "install lands" and "first PR is green" — these
# defaults handle the common cases (no config file, no auto-label config,
# no headers, no .zap suppressions, no gitignore entries) so an adopter's
# first CI run isn't a discovery pass.

seed_template() {
  local label="$1"
  local src="$2"
  local dst="$3"
  if [ ! -f "$src" ]; then
    return 0  # template missing from source (e.g. running an old install.sh against a new repo) — skip silently
  fi
  if [ -f "$dst" ]; then
    info "$label: $dst already exists — leaving it alone"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  success "$label: seeded $dst"
}

# .slopstopper.yml — the adopter's config (seeded from the starter template) is
# seeded earlier, just before sync_mise_cli, so any legacy cli_version pin can
# be read for migration into mise.toml.

# .github/labeler.yml — config for ss-hygiene-auto-label-pr.yml
seed_template ".github/labeler.yml" \
  "$SCRIPT_DIR/templates/labeler.yml.example" \
  "$TARGET_DIR/.github/labeler.yml"

# public/_headers — Cloudflare/Netlify static-asset header baseline (commented out)
#
# Idempotent append-with-markers (same pattern as the .gitignore block
# below). Adopters often arrive with a public/_headers that holds only
# cache rules; a plain skip-if-exists would deny them the security
# baseline forever. Instead: detect our begin-marker; append the block
# bracketed by markers if it isn't there yet; leave existing content
# untouched. The block ships fully commented so adopters opt in by
# uncommenting — same default safety as the fresh-install case.
seed_headers_block() {
  if [ ! -d "$TARGET_DIR/public" ]; then
    info "public/_headers: no public/ directory in target — skipping (add one and re-run if you want the baseline)"
    return 0
  fi
  local dst="$TARGET_DIR/public/_headers"
  local src="$SCRIPT_DIR/templates/_headers.example"
  if [ ! -f "$src" ]; then
    return 0
  fi
  if [ -f "$dst" ] && grep -Fq "# slopstopper security headers begin" "$dst" 2>/dev/null; then
    info "public/_headers: slopstopper security headers block already present — leaving it alone"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  if [ -f "$dst" ] && [ -s "$dst" ]; then
    printf '\n' >> "$dst"
    cat "$src" >> "$dst"
    success "public/_headers: appended slopstopper security headers block (commented; uncomment to enable)"
  else
    cat "$src" > "$dst"
    success "public/_headers: seeded $dst"
  fi
}

seed_headers_block

# .zap/rules.tsv — ZAP rule overrides (entries commented; uncomment what applies)
seed_template ".zap/rules.tsv" \
  "$SCRIPT_DIR/templates/zap-rules.tsv.example" \
  "$TARGET_DIR/.zap/rules.tsv"

# .markdownlint.json — defaults that let real docs pass (MD013 off, etc.).
# Adopters invoke markdownlint directly (`npx markdownlint "docs/**/*.md"`);
# markdownlint auto-discovers the closest config upward, so seeding at repo
# root works whether they call it from root or from docs/.
seed_template ".markdownlint.json" \
  "$SCRIPT_DIR/templates/markdownlint.json.example" \
  "$TARGET_DIR/.markdownlint.json"

# Map Pattern entry-file scaffolds — README.md, AGENTS.md, CLAUDE.md, docs/index.md.
# Templates ship inside the slopstopper-cli wheel under data/templates/entry-files/
# AND in the repo's cli/slopstopper/data/templates/entry-files/ so install.sh can
# resolve them whether running from a clone or from a fresh curl-piped checkout.
# Each file is seeded only when absent — adopters who already have entry files
# keep them untouched. The ss:hygiene:entry-files check enforces the Map Pattern
# pointer rule and emits a paste-ready snippet for any file that exists but
# lacks the pointer; this seed handles only the missing-file case.
ENTRY_FILES_TEMPLATES_DIR="$SCRIPT_DIR/cli/slopstopper/data/templates/entry-files"
seed_template "README.md" \
  "$ENTRY_FILES_TEMPLATES_DIR/README.md" \
  "$TARGET_DIR/README.md"
seed_template "AGENTS.md" \
  "$ENTRY_FILES_TEMPLATES_DIR/AGENTS.md" \
  "$TARGET_DIR/AGENTS.md"
seed_template "CLAUDE.md" \
  "$ENTRY_FILES_TEMPLATES_DIR/CLAUDE.md" \
  "$TARGET_DIR/CLAUDE.md"
seed_template "docs/index.md" \
  "$ENTRY_FILES_TEMPLATES_DIR/docs/index.md" \
  "$TARGET_DIR/docs/index.md"

# .gitignore — append the slopstopper block if not already present.
# Idempotent re-append: the block is bracketed with markers so re-runs
# detect the existing block and skip rather than duplicate.
GI="$TARGET_DIR/.gitignore"
GI_BLOCK_SRC="$SCRIPT_DIR/templates/gitignore.block"
if [ -f "$GI_BLOCK_SRC" ]; then
  if [ -f "$GI" ] && grep -Fq "# slopstopper begin" "$GI" 2>/dev/null; then
    info ".gitignore: slopstopper block already present — leaving it alone"
  else
    [ -f "$GI" ] && [ -s "$GI" ] && printf '\n' >> "$GI"
    cat "$GI_BLOCK_SRC" >> "$GI"
    success ".gitignore: appended slopstopper block"
  fi
fi

# 7. Sweep the rest of the disabled set. The workflow loop above already
# skipped (and cleaned up) every disabled workflow in GENERIC_WORKFLOWS;
# this catches names that aren't in that list — a workflow from an older
# slopstopper release, or one the adopter added and then listed. Driven by
# the same resolved set ($DISABLED_WORKFLOWS = (profile − workflows.enabled)
# ∪ workflows.disabled), so config drives deletions rather than "delete the
# file and trust the marker" — both work, but config-driven is easier to
# audit and survives clone-and-rebuild.
if [ -n "$DISABLED_WORKFLOWS" ]; then
  DISABLED_COUNT=0
  while IFS= read -r wf_name; do
    [ -z "$wf_name" ] && continue
    wf_path="$TARGET_DIR/.github/workflows/$wf_name"
    if [ -f "$wf_path" ]; then
      rm -f "$wf_path"
      (( DISABLED_COUNT++ )) || true
    fi
  done <<< "$DISABLED_WORKFLOWS"
  if [ "$DISABLED_COUNT" -gt 0 ]; then
    info "Removed $DISABLED_COUNT further workflow(s) from the disabled set"
  fi
fi

# ── install Claude Code skills (project level) ──────────────────────────────

# Skills land in <target>/.claude/skills/slopstopper-*/SKILL.md so every
# contributor that clones the repo gets them automatically (Claude Code
# auto-discovers project-level skills the same way as user-level). Disable
# with --no-skills / SLOPSTOPPER_NO_SKILLS.
#
# Same atomic-fetch + frontmatter-validation logic as install-skill.sh:
# fetch each SKILL.md to a temp file, validate it starts with `---`,
# only then overwrite the destination. Re-runs that hit no upstream
# change are no-ops. install-skill.sh remains a standalone way to refresh
# just the skills without re-running the full installer.

SKILL_NAMES=(
  "slopstopper-install"
  "slopstopper-triage"
)
OBSOLETE_SKILLS=(
  "install-slopstopper"
  "slopstopper-update"
)

install_skill_file() {
  local skill="$1"
  local src="https://raw.githubusercontent.com/hungovercoders/slopstopper/main/.claude/skills/${skill}/SKILL.md"
  local dest_dir="${TARGET_DIR}/.claude/skills/${skill}"
  local dest_file="${dest_dir}/SKILL.md"
  local tmp_file
  tmp_file="$(mktemp)"
  # shellcheck disable=SC2064
  trap "rm -f \"${tmp_file}\"" RETURN

  mkdir -p "${dest_dir}"

  if ! curl -fsSL "${src}" -o "${tmp_file}"; then
    warn "Failed to download ${skill}/SKILL.md (non-fatal)."
    return 1
  fi

  if ! head -n 1 "${tmp_file}" | grep -q "^---$"; then
    warn "Downloaded ${skill}/SKILL.md does not look like a skill (no frontmatter). Skipping."
    return 1
  fi

  if [ -f "${dest_file}" ]; then
    if cmp -s "${tmp_file}" "${dest_file}"; then
      info "${skill}: already up to date"
    else
      mv "${tmp_file}" "${dest_file}"
      success "${skill}: refreshed"
    fi
  else
    mv "${tmp_file}" "${dest_file}"
    success "${skill}: installed"
  fi
}

install_claude_skills() {
  if [ "$INSTALL_SKILLS" = "false" ]; then
    info "Skipping Claude Code skill install (--no-skills / SLOPSTOPPER_NO_SKILLS)."
    return 0
  fi

  echo ""
  sep
  echo "  🧠  Installing the SlopStopper Claude Code skills (project level)…"
  sep

  for skill in "${SKILL_NAMES[@]}"; do
    install_skill_file "${skill}" || true
  done

  # Clean up obsolete skill directories left by older installer versions.
  # Only act on directories we know we shipped previously — never delete
  # something the adopter put there.
  for obsolete in "${OBSOLETE_SKILLS[@]}"; do
    obsolete_dir="${TARGET_DIR}/.claude/skills/${obsolete}"
    if [ -d "${obsolete_dir}" ]; then
      rm -rf "${obsolete_dir}"
      info "Removed obsolete skill: ${obsolete}"
    fi
  done

  # Heads-up if the user has stale user-level copies from the old install
  # path — they'll shadow the project-level ones when Claude Code merges
  # skill paths. Don't delete user state silently; surface and let them
  # decide.
  if [ -d "${HOME}/.claude/skills/slopstopper-install" ] \
    || [ -d "${HOME}/.claude/skills/slopstopper-update" ] \
    || [ -d "${HOME}/.claude/skills/slopstopper-triage" ]; then
    warn "Stale user-level skills at ~/.claude/skills/slopstopper-* will shadow the project-level copies."
    info "Clean up with:"
    info "  rm -rf ~/.claude/skills/slopstopper-install \\"
    info "         ~/.claude/skills/slopstopper-update \\"
    info "         ~/.claude/skills/slopstopper-triage"
  fi
}

install_claude_skills

# ── install the pre-push hygiene hook ────────────────────────────────────────
#
# A pre-push hook that runs the fast static hygiene checks (`task
# ss:hygiene:test`) before every push, so the first CI run confirms rather than
# discovers. The hook script is slopstopper-owned and always refreshed (like
# Taskfile.ss.yml); it lives in `.githooks/` (tracked, reviewable) and git is
# pointed at it via `core.hooksPath`.
#
# Respectful wiring: we set core.hooksPath ONLY when it's safe — the adopter
# hasn't already set a custom hooksPath and isn't running another hook manager
# (husky / lefthook / pre-commit). Otherwise we still drop the hook file in but
# leave their git config alone and print a one-line manual opt-in, so we never
# hijack an existing setup. Disable the whole step with --no-hooks.

# True if the target already manages git hooks some other way — a non-default
# core.hooksPath, or a husky / lefthook / pre-commit config. We only auto-wire
# core.hooksPath when none of these exist, mirroring target_has_node_pin's
# "never clobber the adopter's setup" stance.
target_has_hook_manager() {
  local existing
  existing="$(git -C "$TARGET_DIR" config --local --get core.hooksPath 2>/dev/null || true)"
  [ -n "$existing" ] && [ "$existing" != ".githooks" ] && return 0
  [ -d "$TARGET_DIR/.husky" ] && return 0
  [ -f "$TARGET_DIR/lefthook.yml" ] && return 0
  [ -f "$TARGET_DIR/.lefthook.yml" ] && return 0
  [ -f "$TARGET_DIR/lefthook.yaml" ] && return 0
  [ -f "$TARGET_DIR/.pre-commit-config.yaml" ] && return 0
  return 1
}

install_git_hook() {
  if [ "$INSTALL_HOOKS" = "false" ]; then
    info "Skipping pre-push hook install (--no-hooks / SLOPSTOPPER_NO_HOOKS)."
    return 0
  fi

  local src="$SCRIPT_DIR/.githooks/pre-push"
  if [ ! -f "$src" ]; then
    return 0  # running an old checkout without the hook — nothing to install
  fi

  # Not a git repo → nothing to hook into. Not fatal; the rest of the install
  # is still useful.
  if ! git -C "$TARGET_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    info "Target is not a git repository — skipping pre-push hook."
    return 0
  fi

  mkdir -p "$TARGET_DIR/.githooks"
  cp "$src" "$TARGET_DIR/.githooks/pre-push"
  chmod +x "$TARGET_DIR/.githooks/pre-push"

  if target_has_hook_manager; then
    success "pre-push hook written to .githooks/pre-push (refreshed)"
    warn "You already manage git hooks — leaving core.hooksPath alone."
    info "To enable the slopstopper gate, either run:"
    info "    git config core.hooksPath .githooks"
    info "  or add 'task ss:hygiene:test' to your existing hook manager."
  else
    git -C "$TARGET_DIR" config core.hooksPath .githooks
    success "pre-push hook installed (core.hooksPath → .githooks)"
    info "Pushes now run 'task ss:hygiene:test' locally first. Bypass once with 'git push --no-verify'."
  fi
}

install_git_hook

# ── post-install guidance ─────────────────────────────────────────────────────

sep
echo ""
echo "  🎉 Installation complete!"
echo ""
# Surface the pinned version under the banner. Being behind latest is a
# deliberate choice now (the pin), so it's an informational nudge — not an
# alarm — with the one command that moves it.
ss_installed="${SLOPSTOPPER_CLI_VERSION:-}"
ss_latest="${SLOPSTOPPER_CLI_LATEST:-}"
ss_previous="${SLOPSTOPPER_CLI_PREVIOUS:-}"
if [ -n "$ss_installed" ]; then
  if [ -n "$ss_latest" ] && version_lt "$ss_installed" "$ss_latest"; then
    echo "  📦 slopstopper-cli $ss_installed (pinned in mise.toml)"
    info "PyPI latest is $ss_latest — run 'install.sh --upgrade-cli' when you're ready to move the pin."
  elif [ -n "$ss_latest" ]; then
    echo "  📦 slopstopper-cli $ss_installed (pinned, latest on PyPI)"
  else
    echo "  📦 slopstopper-cli $ss_installed (pinned in mise.toml)"
  fi
  # On an actual upgrade, surface old → new and where to read what changed,
  # so an adopter (or agent) isn't left guessing the new feature set.
  if [ -n "$ss_previous" ] && [ "$ss_previous" != "$ss_installed" ]; then
    echo "  ⬆  Upgraded $ss_previous → $ss_installed"
    echo "     What's new: ${REPO_URL%.git}/releases/tag/v${ss_installed}"
  fi
  echo ""
fi
echo "  ── SlopStopper status for this repo ──────────────────────────────"
echo ""
echo "  🧭 Profile: $PROFILE_ACTIVE — $(profile_summary)"
if [ "$PROFILE_SKIPPED" -gt 0 ]; then
  echo "       $PROFILE_SKIPPED check(s) left out as not applying to this shape."
  echo "       'slopstopper profile show' lists them; workflows.enabled keeps one."
fi
echo ""
# Shape suggestion — advisory only, and skipped when the run set the profile
# explicitly. Never applied automatically: a curl-piped install is
# non-interactive, and silently switching checks off is worse than the
# default superset going visibly red.
if [ -z "$PROFILE_FLAG" ]; then
  DETECTED_LINE="$(profile_detect 2>/dev/null || true)"
  DETECTED_NAME="${DETECTED_LINE%%$'\t'*}"
  DETECTED_REASON="${DETECTED_LINE#*$'\t'}"
  if [ -n "$DETECTED_NAME" ] && [ "$DETECTED_NAME" != "$PROFILE_ACTIVE" ]; then
    echo "  💡 This looks more like a '$DETECTED_NAME' repo ($DETECTED_REASON),"
    echo "     which would drop the checks that don't apply to that shape."
    echo "     To switch, set this in .slopstopper.yml and re-run install.sh:"
    echo ""
    echo "       profile: $DETECTED_NAME"
    echo ""
    echo "     Nothing was changed for you — see 'slopstopper profile list'."
    echo ""
  fi
fi
echo "  ✅ Active now (no config needed — work on any code):"
echo "       SAST · Secrets · Dependency CVEs · Dependency Review"
echo "       Complexity · Doc Structure · Doc Accuracy · Doc Size"
echo "       Auto-label PRs · Workflow-failure tracker"
echo ""
if [ "$INSTALL_HOOKS" = "true" ]; then
  echo "  🪝 Local pre-push gate: the hygiene checks run before every push"
  echo "       (task ss:hygiene:test) so CI confirms rather than discovers."
  echo "       Bypass a single push with 'git push --no-verify'."
  echo ""
fi
# Which URL-driven checks this repo actually carries depends on the
# profile, so build the list from what landed on disk rather than naming
# them all unconditionally.
DYNAMIC_LABELS=""
add_dynamic_label() {
  [ -f "$TARGET_DIR/.github/workflows/$1" ] || return 0
  if [ -z "$DYNAMIC_LABELS" ]; then
    DYNAMIC_LABELS="$2"
  else
    DYNAMIC_LABELS="$DYNAMIC_LABELS · $2"
  fi
}
add_dynamic_label "ss-reliability-smoke-tests.yml"          "Smoke"
add_dynamic_label "ss-reliability-accessibility-check.yml"  "Accessibility"
add_dynamic_label "ss-reliability-core-web-vitals.yml"      "Core Web Vitals"
add_dynamic_label "ss-security-dast-check.yml"              "DAST"
add_dynamic_label "ss-reliability-seo-check.yml"            "SEO"
add_dynamic_label "ss-reliability-broken-links-check.yml"   "Broken Links"
add_dynamic_label "ss-reliability-llms-txt-check.yml"       "llms.txt"
add_dynamic_label "ss-reliability-robots-txt-check.yml"     "robots.txt"
add_dynamic_label "ss-reliability-sitemap-check.yml"        "Sitemap"
add_dynamic_label "ss-reliability-api-health-check.yml"     "API Health"
add_dynamic_label "ss-reliability-api-latency-check.yml"    "API Latency"
add_dynamic_label "ss-security-api-headers-check.yml"       "API Headers"
add_dynamic_label "ss-hygiene-openapi-check.yml"            "OpenAPI Drift"

if [ -n "$DYNAMIC_LABELS" ]; then
  echo "  ⏳ Active once you point them at your app (edit .slopstopper.yml):"
  echo "       $DYNAMIC_LABELS"
  echo ""
  echo "     # in .slopstopper.yml:"
  echo "     urls:"
  echo "       production: https://your-site.example.com"
  echo "       preview:    https://staging.your-site.example.com"
  echo ""
  echo "     # if you need a different Node version for your build (pinned in"
  echo "     # mise.toml, read by mise locally and CI):"
  echo "     mise use node@22"
  echo ""
else
  echo "  ⏸ URL-driven checks: none installed — profile '$PROFILE_ACTIVE' has no"
  echo "       served surface to audit, so nothing here needs a URL."
  echo "       Take one back with workflows.enabled in .slopstopper.yml."
  echo ""
fi
echo "  🔐 Inert until you add secrets in your repo settings:"
echo "       Doc Auto-Updater (gh-aw agentic workflow)"
echo "         → COPILOT_GITHUB_TOKEN"
echo "         → Settings → Actions → General →"
echo "           'Allow GitHub Actions to create and approve pull requests'"
echo "         → See docs/hygiene/DOC_UPDATER.md for the full setup"
echo ""
echo "  🚀 Deploy is handled by Cloudflare, not by a workflow in this suite:"
echo "       Cloudflare dash → Workers & Pages → Create → Connect to Git"
echo "       Pushes deploy to prod, PRs get preview URLs, closing a PR"
echo "       cleans up the preview. No GitHub secrets required."
echo "       See docs/deployment/README.md for the full cutover steps."
echo ""
echo "  Don't use the doc-updater? Just delete its workflows from"
echo "  .github/workflows/ — re-running this installer won't bring them"
echo "  back (tracked via .ss/.workflows-installed)."
echo ""
sep
echo ""
if [ "$USE_TASK" = "true" ]; then
  echo "  Canonical invocation: task ss:<check>"
  echo ""
  echo "    Workflows are Task-driven by default — task ss:<check> is the"
  echo "    canonical interface for humans, agents and CI alike, so the"
  echo "    suite sits naturally alongside any other task build / task"
  echo "    deploy tasks in your codebase. The workflows install Task"
  echo "    themselves; locally, install it via:"
  echo ""
  echo "       https://taskfile.dev/installation/"
  echo ""
  echo "    Don't want Task in your CI? Re-run install.sh with --no-task"
  echo "    to get workflows that call slopstopper-cli directly:"
  echo ""
  echo "       bash install.sh --no-task"
  echo ""
  echo "  Next steps:"
  echo "    1. Install the Task runner (if you don't have it):"
  echo "         curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin"
  echo "    2. npm install"
  echo "    3. task --list"
  echo "    4. slopstopper badges          # generate README status badges (paste into README.md)"
  echo "    5. Open a PR — every check runs automatically."
else
  echo "  Installed in --no-task mode."
  echo ""
  echo "    Workflows call slopstopper-cli directly (no Task install step,"
  echo "    no task ss:* invocations). To switch to the canonical Task-driven"
  echo "    flow later, re-run install.sh without --no-task."
  echo ""
  echo "  Next steps:"
  echo "    1. npm install"
  echo "    2. slopstopper checks list      # see every check shipped"
  echo "    3. slopstopper badges           # generate README status badges (paste into README.md)"
  echo "    4. Open a PR — every check runs automatically."
fi
echo ""
sep
