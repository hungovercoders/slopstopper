#!/usr/bin/env bash
# install-skill.sh — install the SlopStopper Claude Code skills.
#
# The companion to install.sh: install.sh drops the quality suite into a
# *repo*, this script drops the SlopStopper skill trio into your Claude
# Code *user profile* so they're available in every project on this
# machine. Run it once per machine; re-run any time to refresh.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
#
# Or, two-step (review first):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh -o install-skill.sh
#   bash install-skill.sh
#
# What lands:
#   ~/.claude/skills/slopstopper-install/SKILL.md   # first-time install
#   ~/.claude/skills/slopstopper-update/SKILL.md    # refresh an existing install
#   ~/.claude/skills/slopstopper-triage/SKILL.md    # diagnose a failing check
#
# Migration:
#   If a previous version of this script installed the skill at
#   ~/.claude/skills/install-slopstopper/, this script removes that
#   obsolete directory after installing the trio. The single-skill name
#   is replaced by `slopstopper-install` in the trio layout.
#
# What this affects:
#   Nothing outside ~/.claude/skills/slopstopper-*/. Re-running the
#   script overwrites each SKILL.md in place only if the upstream
#   content differs — safe to refresh on a schedule.

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/hungovercoders/slopstopper/main"
SKILLS=(
  "slopstopper-install"
  "slopstopper-update"
  "slopstopper-triage"
)
OBSOLETE_SKILLS=(
  "install-slopstopper"
)

# ── helpers ──────────────────────────────────────────────────────────────────

info()    { echo "  ℹ  $*"; }
success() { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
error()   { echo "  ❌ $*" >&2; exit 1; }

sep() { echo "────────────────────────────────────────────────────────────"; }

# ── preflight ────────────────────────────────────────────────────────────────

command -v curl >/dev/null 2>&1 || error "curl is required to fetch the skills. Install it and re-run."

if [ ! -d "${HOME}/.claude" ]; then
  warn "${HOME}/.claude does not exist yet."
  info "That's fine — this script will create the skills directory. If you"
  info "haven't installed Claude Code, Claude Code will pick the skills up"
  info "automatically once you do (https://claude.com/claude-code)."
fi

sep
echo "  🧠  SlopStopper — installing the Claude Code skill trio"
echo "  Source : ${REPO_RAW}/.claude/skills/<skill>/SKILL.md"
echo "  Target : ${HOME}/.claude/skills/<skill>/SKILL.md"
sep

# ── install each skill ──────────────────────────────────────────────────────

# Atomic fetch via temp file per skill: only overwrite the destination
# if the download succeeded AND looks like a Claude Code skill (frontmatter
# present). An interrupted install can't leave a half-file behind.
install_skill() {
  local skill="$1"
  local src="${REPO_RAW}/.claude/skills/${skill}/SKILL.md"
  local dest_dir="${HOME}/.claude/skills/${skill}"
  local dest_file="${dest_dir}/SKILL.md"
  local tmp_file
  tmp_file="$(mktemp)"
  # shellcheck disable=SC2064 # we want $tmp_file expanded now, not on EXIT
  trap "rm -f \"${tmp_file}\"" RETURN

  mkdir -p "${dest_dir}"

  if ! curl -fsSL "${src}" -o "${tmp_file}"; then
    error "Failed to download ${skill}/SKILL.md from ${src}"
  fi

  if ! head -n 1 "${tmp_file}" | grep -q "^---$"; then
    error "Downloaded ${skill}/SKILL.md does not look like a Claude Code skill (no frontmatter). Aborting."
  fi

  if [ -f "${dest_file}" ]; then
    if cmp -s "${tmp_file}" "${dest_file}"; then
      success "${skill} already up to date — no changes."
    else
      mv "${tmp_file}" "${dest_file}"
      success "${skill} refreshed."
    fi
  else
    mv "${tmp_file}" "${dest_file}"
    success "${skill} installed."
  fi
}

for skill in "${SKILLS[@]}"; do
  install_skill "${skill}"
done

# ── clean up obsolete skill directories ──────────────────────────────────────

# Adopters who ran an earlier version of this script have an obsolete skill
# at the old path. Remove it so their `~/.claude/skills/` only contains the
# current trio. Safe because the trio supersedes the old one; we never
# delete anything we didn't put there ourselves.
for obsolete in "${OBSOLETE_SKILLS[@]}"; do
  obsolete_dir="${HOME}/.claude/skills/${obsolete}"
  if [ -d "${obsolete_dir}" ]; then
    rm -rf "${obsolete_dir}"
    info "Removed obsolete skill: ${obsolete} (replaced by slopstopper-install)"
  fi
done

# ── post-install guidance ────────────────────────────────────────────────────

sep
echo ""
echo "  🎉 Skill trio installed!"
echo ""
echo "  Claude Code will auto-discover each one in every project on this"
echo "  machine. The skill that triggers depends on what the prompt asks:"
echo ""
echo "    • \"install slopstopper\"           → slopstopper-install"
echo "    • \"refresh / upgrade slopstopper\" → slopstopper-update"
echo "    • \"fix this failing slopstopper check\" → slopstopper-triage"
echo ""
echo "  To install SlopStopper into a repo for the first time:"
echo "    cd <your-repo>"
echo "    curl -fsSL ${REPO_RAW}/install.sh | bash"
echo ""
echo "  Re-running this script later refreshes the trio to latest."
echo ""
sep
