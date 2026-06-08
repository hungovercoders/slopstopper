#!/usr/bin/env bash
# install-skill.sh — install the SlopStopper Claude Code skill.
#
# The companion to install.sh: install.sh drops the quality suite into a
# *repo*, this script drops the install-slopstopper skill into your
# Claude Code *user profile* so it's available in every project on this
# machine. Run it once per machine.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
#
# Or, two-step (review first):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh -o install-skill.sh
#   bash install-skill.sh
#
# What lands:
#   ~/.claude/skills/install-slopstopper/SKILL.md
#
# What this affects:
#   Nothing outside ~/.claude/skills/install-slopstopper/. Re-running the
#   script overwrites the SKILL.md in place so you always get the latest
#   guidance — the skill is small, self-contained, and safe to refresh.

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/hungovercoders/slopstopper/main"
SKILL_PATH=".claude/skills/install-slopstopper/SKILL.md"
DEST_DIR="${HOME}/.claude/skills/install-slopstopper"
DEST_FILE="${DEST_DIR}/SKILL.md"

# ── helpers ──────────────────────────────────────────────────────────────────

info()    { echo "  ℹ  $*"; }
success() { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
error()   { echo "  ❌ $*" >&2; exit 1; }

sep() { echo "────────────────────────────────────────────────────────────"; }

# ── preflight ────────────────────────────────────────────────────────────────

command -v curl >/dev/null 2>&1 || error "curl is required to fetch the skill. Install it and re-run."

if [ ! -d "${HOME}/.claude" ]; then
  warn "${HOME}/.claude does not exist yet."
  info "That's fine — this script will create the skills directory. If you"
  info "haven't installed Claude Code, Claude Code will pick the skill up"
  info "automatically once you do (https://claude.com/claude-code)."
fi

sep
echo "  🧠  SlopStopper — installing the Claude Code skill"
echo "  Source : ${REPO_RAW}/${SKILL_PATH}"
echo "  Target : ${DEST_FILE}"
sep

# ── install ──────────────────────────────────────────────────────────────────

mkdir -p "${DEST_DIR}"

# Atomic fetch via temp file: only overwrite the destination if the
# download succeeded, so an interrupted install can't leave a half-file
# behind.
TMP_FILE="$(mktemp)"
trap 'rm -f "${TMP_FILE}"' EXIT

if ! curl -fsSL "${REPO_RAW}/${SKILL_PATH}" -o "${TMP_FILE}"; then
  error "Failed to download SKILL.md from ${REPO_RAW}/${SKILL_PATH}"
fi

# Sanity-check the file looks like a Claude Code skill (frontmatter present)
# before we overwrite anything.
if ! head -n 1 "${TMP_FILE}" | grep -q "^---$"; then
  error "Downloaded file does not look like a Claude Code skill (no frontmatter). Aborting."
fi

if [ -f "${DEST_FILE}" ]; then
  if cmp -s "${TMP_FILE}" "${DEST_FILE}"; then
    success "Skill already up to date — no changes."
  else
    mv "${TMP_FILE}" "${DEST_FILE}"
    success "Skill refreshed (existing SKILL.md was older)."
  fi
else
  mv "${TMP_FILE}" "${DEST_FILE}"
  success "Skill installed."
fi

# ── post-install guidance ────────────────────────────────────────────────────

sep
echo ""
echo "  🎉 Skill installed!"
echo ""
echo "  Claude Code will auto-discover it in every project on this machine."
echo "  Any prompt that asks to add SlopStopper — e.g. \"install slopstopper\""
echo "  or \"add the slopstopper quality suite\" — will invoke the skill."
echo ""
echo "  To install SlopStopper into a repo:"
echo "    cd <your-repo>"
echo "    curl -fsSL ${REPO_RAW}/install.sh | bash"
echo ""
echo "  Re-running this script later refreshes the skill to latest."
echo ""
sep
