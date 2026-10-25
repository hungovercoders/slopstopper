#!/usr/bin/env bash
# install.sh: bootstrap the SlopStopper suite into a target repository.
#
# It does the one thing the CLI cannot do for itself: pin slopstopper-cli
# (with task and node) in the target's mise.toml and install that version
# through mise. Then it hands over. `mise exec -- slopstopper install` writes
# the suite (the ss-*.yml workflows and composite actions, the task ss:*
# shims, the seeds, the .gitignore block, the pre-push hook, the Claude Code
# skills) from the files that version of the CLI ships, so a repo's shims
# always name checks its CLI knows, and a refresh writes the pinned
# version's suite rather than whatever is on main. Every flag the CLI
# understands is passed through; `slopstopper install --help` lists what it
# writes and leaves alone.
#
# Usage (one-liner from GitHub, review the script first):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
#
# Usage (two-step, so the script is on disk to read):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
#   bash install.sh [TARGET_DIR]
#
# No checkout of the slopstopper repository is needed: the suite comes from
# the slopstopper-cli wheel on PyPI.

set -euo pipefail

REPO_URL="https://github.com/hungovercoders/slopstopper"

# ── argument parsing ─────────────────────────────────────────────────────────
#
# The pin is this script's: --upgrade-cli and --cli-version move it (both
# wrap `mise use`), and a plain run honours it. Everything else is the CLI's
# and goes through untouched; the SLOPSTOPPER_* env vars the flags mirror
# are read by the CLI itself.

UPGRADE_CLI=false
CLI_VERSION_FLAG=""
PASSTHROUGH=()
POSITIONAL=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --profile)
      [ -n "${2:-}" ] || { echo "  ❌ --profile requires a name (e.g. --profile api)" >&2; exit 1; }
      PASSTHROUGH+=("$1" "$2")
      shift 2
      ;;
    --profile=*)
      [ -n "${1#*=}" ] || { echo "  ❌ --profile requires a name (e.g. --profile=api)" >&2; exit 1; }
      PASSTHROUGH+=("$1")
      shift
      ;;
    --no-task|--no-skills|--no-hooks|--no-topic)
      PASSTHROUGH+=("$1")
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
install.sh: install the SlopStopper quality suite into a target repo.

Usage:
  bash install.sh [TARGET_DIR]                 # Task-driven workflows (default)
  bash install.sh --no-task [TARGET_DIR]       # CLI-driven workflows (no Task in CI)
  bash install.sh --no-skills [TARGET_DIR]     # Skip the Claude Code skills
  bash install.sh --no-hooks [TARGET_DIR]      # Skip the pre-push hygiene hook
  bash install.sh --no-topic [TARGET_DIR]      # Don't add the `slopstopper` repo topic via gh
  bash install.sh --profile api [TARGET_DIR]   # Install the check set for a repo of that shape
  bash install.sh --upgrade-cli [TARGET_DIR]   # Bump the pinned CLI to the latest on PyPI
  bash install.sh --cli-version X.Y.Z [TARGET] # Pin the CLI to an exact version

Env var equivalents:
  SLOPSTOPPER_NO_TASK=1 bash install.sh
  SLOPSTOPPER_NO_SKILLS=1 bash install.sh
  SLOPSTOPPER_NO_HOOKS=1 bash install.sh
  SLOPSTOPPER_NO_TOPIC=1 bash install.sh
  SLOPSTOPPER_PROFILE=api bash install.sh

This script pins slopstopper-cli (with task and node) in the target's
mise.toml and installs that version through mise, which activates it
per-directory so the active version follows the repo. A plain run installs
the pinned version and never moves the pin; a first install pins the latest
published version; --upgrade-cli and --cli-version move it (both wrap
`mise use`). mise is required: https://mise.jdx.dev. A legacy
.slopstopper.yml cli_version pin is migrated into mise.toml on the next run.

It then runs `slopstopper install` from that pinned CLI, which writes the
suite from the files the CLI ships: the ss-*.yml workflows and composite
actions, the task ss:* shims, a starter .slopstopper.yml, the seeds a green
first PR needs, the pre-push hygiene hook and the Claude Code skills. The
flags above that are not about the pin go straight through to it;
`slopstopper install --help` describes each, the profiles, and what a re-run
refreshes and leaves alone.
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
# failure (offline, no curl, malformed JSON). Callers treat empty as
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

# Run the pinned slopstopper-cli: through mise in the target when mise did
# the install, else whatever `slopstopper` is on PATH (the SKIP_CLI_INSTALL
# test seam, which has no mise). A bare `slopstopper` is wrong right after
# the pin moves: in PATH-activation mode the shell keeps the old binary
# until it re-enters the directory, and without activation there is none.
pinned_cli() {
  if [ "${SKIP_CLI_INSTALL:-0}" != "1" ] && command -v mise >/dev/null 2>&1; then
    ( cd "$TARGET_DIR" 2>/dev/null && mise exec -- slopstopper "$@" )
  else
    slopstopper "$@"
  fi
}

# version_lt A B → exit 0 if A is strictly older than B (semver ordering).
version_lt() {
  [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" = "$1" ]
}

# Path to the target's mise config, which holds the canonical pin. Prefer
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

# Legacy parse: the pre-mise pin lived in .slopstopper.yml (cli_version:).
# Read it so a refresh pins that version; the CLI strips the dead key.
read_legacy_cli_version() {
  [ -f "$1" ] || return 0
  sed -n 's/^cli_version:[[:space:]]*["'\'']\{0,1\}\([0-9][0-9.]*\).*/\1/p' "$1" | head -1
}

# Set a [tools] entry in a mise config, portable across BSD/GNU and offline.
# It needs no mise binary, which the SKIP_CLI_INSTALL test seam relies on. Real
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

# Default Node version seeded into a fresh adopter mise config. Node is a tool
# version, so it belongs in mise (not .slopstopper.yml); the ss-*.yml
# workflows get it from this pin via jdx/mise-action, so they need no setup-node step.
DEFAULT_NODE_VERSION="20"

# True if the target already declares a Node version in a place mise (and the
# workflows) honour: a `node` [tools] entry in the mise config or a
# .node-version / .nvmrc file. The node pin is seeded only when none of these
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
  pinned_cli --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true
}

# slopstopper-cli version the caller's shell resolves from the target, i.e.
# what a bare `slopstopper` runs there right now. `mise activate` puts the
# pinned version's install dir on PATH and only refreshes it when the prompt
# hook fires, so after the pin moves the shell that ran install.sh keeps the
# old binary until the user re-enters the directory. Empty if not on PATH.
shell_cli_version() {
  ( cd "$TARGET_DIR" 2>/dev/null && installed_cli_version )
}

# ── prerequisite check ────────────────────────────────────────────────────────
#
# mise installs the pinned CLI through its pipx backend, which needs a Python.
# Everything the checks themselves need is the CLI's to report
# (`slopstopper doctor`), so nothing else blocks the install.

preflight() {
  local missing=()
  command -v python3 >/dev/null 2>&1 || missing+=("python3 (slopstopper-cli is a Python package): https://www.python.org/downloads/")
  if [ "${SKIP_CLI_INSTALL:-0}" != "1" ]; then
    command -v mise >/dev/null 2>&1 || missing+=("mise (installs the pinned slopstopper-cli + task): https://mise.jdx.dev")
  fi
  if [ "${#missing[@]}" -gt 0 ]; then
    for tool in "${missing[@]}"; do
      echo "  ❌ Required tool missing: $tool" >&2
    done
    error "Install the tools above and re-run."
  fi
}

preflight

[ -d "$TARGET_DIR" ] || error "Target directory does not exist: $TARGET_DIR"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

sep
echo "  🛠  SlopStopper: pinning and installing slopstopper-cli"
echo "  Target : $TARGET_DIR"
sep

# ── pin and install the CLI ───────────────────────────────────────────────────

# Decide which version to pin:
#   --cli-version X.Y.Z  → that exact version
#   --upgrade-cli        → the latest on PyPI
#   mise pin already set → honour it (a plain refresh never moves the pin)
#   legacy cli_version   → migrate it (first move off the old mechanism)
#   nothing yet          → latest on PyPI (first install records it)
SS_LATEST="$(latest_pypi_version)"

resolve_pinned_version() {
  local existing legacy
  existing="$(read_mise_cli_version "$(mise_config_path)")"
  legacy="$(read_legacy_cli_version "$TARGET_DIR/.slopstopper.yml")"
  if [ -n "$CLI_VERSION_FLAG" ]; then
    echo "$CLI_VERSION_FLAG"
  elif [ "$UPGRADE_CLI" = "true" ]; then
    echo "$SS_LATEST"
  elif [ -n "$existing" ]; then
    echo "$existing"
  elif [ -n "$legacy" ]; then
    echo "$legacy"
  else
    echo "$SS_LATEST"
  fi
}

sync_mise_cli() {
  local mcfg pre_version pinned
  mcfg="$(mise_config_path)"
  pre_version="$(read_mise_cli_version "$mcfg")"
  pinned="$(resolve_pinned_version)"

  # Escape hatch for cli/tests/test_install.py: write the pin into mise.toml
  # offline (no mise binary, no PyPI) so tests can assert on it deterministically.
  if [ "${SKIP_CLI_INSTALL:-0}" = "1" ]; then
    [ -n "$pinned" ] && write_mise_tool "$mcfg" "pipx:slopstopper-cli" "$pinned"
    write_mise_tool "$mcfg" "task" "3"
    target_has_node_pin "$mcfg" || write_mise_tool "$mcfg" "node" "$DEFAULT_NODE_VERSION"
    info "Skipping mise install (SKIP_CLI_INSTALL=1)"
    SLOPSTOPPER_CLI_VERSION="$pinned"
    SLOPSTOPPER_CLI_PREVIOUS="$pre_version"
    SLOPSTOPPER_CLI_SHELL="$(shell_cli_version)"
    return 0
  fi

  # `mise use` edits mise.toml AND installs the tool in one idempotent step,
  # and it handles a moved pin (upgrade or downgrade) deterministically. Pin
  # `task` too so mise provides the canonical interface. Seed `node` only when
  # the adopter hasn't already declared one (mise.toml / .node-version /
  # .nvmrc), so their build's Node version is never overridden.
  local node_arg=""
  target_has_node_pin "$mcfg" || node_arg="node@$DEFAULT_NODE_VERSION"
  if [ -n "$pinned" ]; then
    info "Pinning slopstopper-cli@$pinned (+ task) in $(basename "$mcfg") via mise…"
    mise use --path "$mcfg" "pipx:slopstopper-cli@$pinned" "task@3" $node_arg >/dev/null \
      || error "mise use failed. Check the version exists on PyPI and your network, then retry."
  else
    warn "Could not determine a slopstopper-cli version (offline?). Only task and node are pinned; pass --cli-version X.Y.Z, or retry with the network, to pin and install the CLI."
    mise use --path "$mcfg" "task@3" $node_arg >/dev/null || true
  fi

  # In shims mode a reshim points `slopstopper` at the new pin straight away.
  # In PATH-activation mode it changes nothing; the banner says what to do.
  mise reshim >/dev/null 2>&1 || true

  # mise installs into its own dir; the binary is only on PATH if mise is
  # activated in this shell, which it may not be. Validate via `mise exec`
  # within the target so the check is activation-independent.
  if ! ( cd "$TARGET_DIR" 2>/dev/null && mise which slopstopper >/dev/null 2>&1 ); then
    [ -n "$pinned" ] || error "No slopstopper-cli is pinned, so there is nothing to run 'slopstopper install'. Pass --cli-version X.Y.Z, or retry with the network."
    error "mise installed slopstopper-cli but can't resolve the 'slopstopper' binary. Ensure mise is set up and activated: https://mise.jdx.dev/getting-started.html"
  fi

  local post_version
  post_version="$(mise_active_cli_version)"

  # The active version must match the pin we asked for. A mismatch means the
  # pinned version doesn't exist on PyPI or a mirror served stale data, so fail
  # loudly rather than limp on the wrong version.
  if [ -n "$post_version" ] && [ "$post_version" != "$pinned" ]; then
    error "Asked for slopstopper-cli@$pinned but $post_version is active. Verify the version exists on PyPI, then run 'mise install' in $TARGET_DIR."
  fi

  success "slopstopper-cli installed ($post_version, pinned in $(basename "$mcfg"))"

  # Stash facts for the closing notes. LATEST is informational only,
  # because a pin behind latest is a deliberate choice, not a fault.
  SLOPSTOPPER_CLI_VERSION="$post_version"
  SLOPSTOPPER_CLI_PREVIOUS="$pre_version"
  SLOPSTOPPER_CLI_SHELL="$(shell_cli_version)"
}

sync_mise_cli

# ── hand over to the pinned CLI ───────────────────────────────────────────────
#
# Everything from here is the CLI's: it writes the suite from its own wheel,
# refreshes what slopstopper owns, respects a deleted workflow, prints what
# landed and what still needs config. It exits 1 on a refusal (an unknown
# --profile, a target that is not a directory) before touching the repo.

echo ""
pinned_cli install ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"} "$TARGET_DIR" \
  || error "slopstopper install did not complete; see the messages above."

# ── the pin, in closing ───────────────────────────────────────────────────────
#
# The CLI's banner has named the pin; these are the three things it cannot
# know. Being behind latest is a deliberate choice (the pin), so it is an
# informational nudge rather than an alarm, naming the one command that moves it.
ss_installed="${SLOPSTOPPER_CLI_VERSION:-}"
ss_latest="$SS_LATEST"
ss_previous="${SLOPSTOPPER_CLI_PREVIOUS:-}"
if [ -n "$ss_installed" ]; then
  echo ""
  if [ -n "$ss_latest" ] && version_lt "$ss_installed" "$ss_latest"; then
    info "PyPI latest is $ss_latest. Run 'install.sh --upgrade-cli' when you're ready to move the pin."
  elif [ -n "$ss_latest" ]; then
    info "slopstopper-cli $ss_installed is the latest on PyPI."
  fi
  # On an actual upgrade, surface old → new and where to read what changed,
  # so an adopter (or agent) isn't left guessing the new feature set.
  if [ -n "$ss_previous" ] && [ "$ss_previous" != "$ss_installed" ]; then
    echo "  ⬆  Upgraded $ss_previous → $ss_installed"
    echo "     What's new: $REPO_URL/releases/tag/v${ss_installed}"
  fi
  # The pin moved but this shell still resolves the old binary, so a local
  # check loop run straight after the install would test the wrong version.
  ss_shell="${SLOPSTOPPER_CLI_SHELL:-}"
  if [ -n "$ss_shell" ] && [ "$ss_shell" != "$ss_installed" ]; then
    warn "This shell still runs slopstopper $ss_shell, not the pinned $ss_installed."
    echo "     Re-enter the directory (cd out and back in) so mise re-activates,"
    echo "     or run: eval \"\$(mise activate bash)\"   (zsh/fish: swap the shell name)"
    echo "     Until then, use: mise exec -- slopstopper …"
  fi
  echo ""
fi
