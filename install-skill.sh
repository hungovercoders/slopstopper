#!/usr/bin/env bash
# install-skill.sh — install/refresh the SlopStopper Claude Code skills
# into the target repo.
#
# The companion to install.sh: install.sh installs the whole quality suite
# into a repo; this script just covers the skill subset, so you can refresh
# just the playbooks without touching workflows, the Taskfile or the CLI.
#
# Skills are installed at *project level* — into the adopter repo's
# ./.claude/skills/ directory — so every contributor that clones the repo
# gets them automatically (Claude Code auto-discovers project-level skills
# the same way it does user-level ones). Commit the resulting files
# alongside the workflows.
#
# Usage (from inside the target repo):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
#
# Or, two-step (review first):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh -o install-skill.sh
#   bash install-skill.sh
#
# Or, explicit target directory:
#   bash install-skill.sh /path/to/repo
#
# What lands:
#   <target>/.claude/skills/slopstopper-install/   # install + refresh (SKILL.md + references/)
#   <target>/.claude/skills/slopstopper-triage/    # diagnose a failing check
#
# Migration:
#   - If a previous version installed a single `install-slopstopper` skill,
#     that obsolete directory is removed from the target repo.
#   - The `slopstopper-update` skill has been folded into `slopstopper-install`
#     (which now covers both first-install and refresh). Any stale
#     `slopstopper-update/` directory in the target is removed.
#   - This script no longer writes to ~/.claude/skills/. If a previous
#     version installed copies there, they'll shadow the project-level ones
#     when Claude Code merges skill paths — remove them manually with:
#       rm -rf ~/.claude/skills/slopstopper-install \
#              ~/.claude/skills/slopstopper-update \
#              ~/.claude/skills/slopstopper-triage
#
# What this affects:
#   Nothing outside <target>/.claude/skills/slopstopper-*/. Re-running
#   replaces each skill directory only if the upstream content differs —
#   safe to refresh on a schedule.

set -euo pipefail

# Override to fetch from a mirror or a local checkout (file:///path/to/slopstopper).
REPO_RAW="${SLOPSTOPPER_REPO_RAW:-https://raw.githubusercontent.com/hungovercoders/slopstopper/main}"
SKILLS=(
  "slopstopper-install"
  "slopstopper-triage"
)
OBSOLETE_SKILLS=(
  "install-slopstopper"
  "slopstopper-update"
)

# ── argument parsing ─────────────────────────────────────────────────────────

TARGET_DIR="${1:-$(pwd)}"

# ── helpers ──────────────────────────────────────────────────────────────────

info()    { echo "  ℹ  $*"; }
success() { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
error()   { echo "  ❌ $*" >&2; exit 1; }

sep() { echo "────────────────────────────────────────────────────────────"; }

# ── preflight ────────────────────────────────────────────────────────────────

command -v curl >/dev/null 2>&1 || error "curl is required to fetch the skills. Install it and re-run."

if [ ! -d "${TARGET_DIR}" ]; then
  error "Target directory does not exist: ${TARGET_DIR}"
fi

sep
echo "  🧠  SlopStopper — installing the Claude Code skills (project level)"
echo "  Source : ${REPO_RAW}/.claude/skills/<skill>/  (SKILL.md + references/)"
echo "  Target : ${TARGET_DIR}/.claude/skills/<skill>/"
sep

# ── install each skill ──────────────────────────────────────────────────────

SKILLS_RAW="${REPO_RAW}/.claude/skills"
# Standalone script: there is no checkout to copy from, so SKILLS_SRC_DIR
# stays unset and every file is fetched. install.sh sets it.
SKILLS_SRC_DIR=""
SKILL_FAIL() { error "$*"; }

# A skill is a directory: SKILL.md plus the references/*.md files it links
# (the long tables live there and are read on demand, so the skill costs one
# page of context until a step needs detail). Running from a checkout copies
# the directory; a curl-piped install fetches SKILL.md, validates it, then
# fetches every references/<name>.md it mentions. Either way the result is
# staged in a temp dir and swapped in whole, so an interrupted run cannot
# leave a half-skill behind.
install_skill_dir() {
  local skill="$1"
  local dest_dir="${TARGET_DIR}/.claude/skills/${skill}"
  local stage
  stage="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf \"${stage}\"" RETURN

  if [ -n "${SKILLS_SRC_DIR:-}" ] && [ -f "${SKILLS_SRC_DIR}/${skill}/SKILL.md" ]; then
    cp -R "${SKILLS_SRC_DIR}/${skill}/." "${stage}/"
  else
    if ! curl -fsSL "${SKILLS_RAW}/${skill}/SKILL.md" -o "${stage}/SKILL.md"; then
      SKILL_FAIL "Failed to download ${skill}/SKILL.md"
      return 1
    fi
    local ref
    for ref in $(grep -o 'references/[A-Za-z0-9_.-]*\.md' "${stage}/SKILL.md" | sort -u); do
      mkdir -p "${stage}/references"
      if ! curl -fsSL "${SKILLS_RAW}/${skill}/${ref}" -o "${stage}/${ref}"; then
        SKILL_FAIL "Failed to download ${skill}/${ref}"
        return 1
      fi
    done
  fi

  if ! head -n 1 "${stage}/SKILL.md" | grep -q "^---$"; then
    SKILL_FAIL "${skill}/SKILL.md does not look like a Claude Code skill (no frontmatter). Skipping."
    return 1
  fi

  if [ -d "${dest_dir}" ] && diff -rq "${stage}" "${dest_dir}" >/dev/null 2>&1; then
    info "${skill}: already up to date"
    return 0
  fi
  local had_it=false
  [ -d "${dest_dir}" ] && had_it=true
  mkdir -p "$(dirname "${dest_dir}")"
  rm -rf "${dest_dir}"
  cp -R "${stage}" "${dest_dir}"
  if [ "${had_it}" = true ]; then success "${skill}: refreshed"; else success "${skill}: installed"; fi
}

for skill in "${SKILLS[@]}"; do
  install_skill_dir "${skill}"
done

# ── clean up obsolete skill directories ──────────────────────────────────────

# Adopters who ran an earlier version of this script have obsolete skills
# at superseded paths. Remove them so their <target>/.claude/skills/ only
# contains the current set. Safe because we never delete anything we didn't
# put there ourselves:
#   - `install-slopstopper` was the single-skill name; replaced by the
#     `slopstopper-install` trio member.
#   - `slopstopper-update` was a separate refresh skill; its content has
#     been folded into `slopstopper-install` (covers both verbs).
for obsolete in "${OBSOLETE_SKILLS[@]}"; do
  obsolete_dir="${TARGET_DIR}/.claude/skills/${obsolete}"
  if [ -d "${obsolete_dir}" ]; then
    rm -rf "${obsolete_dir}"
    info "Removed obsolete skill: ${obsolete}"
  fi
done

# Heads-up: if the adopter ran an old version of install-skill.sh on this
# machine, they likely have stale copies of the same skills at user level
# (~/.claude/skills/slopstopper-*). Those will shadow the project-level
# copies when Claude Code merges skill paths. We don't delete user-level
# state on someone's behalf — but we point at it so they can clean up
# explicitly.
if [ -d "${HOME}/.claude/skills/slopstopper-install" ] \
  || [ -d "${HOME}/.claude/skills/slopstopper-update" ] \
  || [ -d "${HOME}/.claude/skills/slopstopper-triage" ]; then
  warn "Stale user-level skills detected at ~/.claude/skills/slopstopper-*."
  info "They'll shadow the project-level copies you just installed. Clean up with:"
  info "  rm -rf ~/.claude/skills/slopstopper-install \\"
  info "         ~/.claude/skills/slopstopper-update \\"
  info "         ~/.claude/skills/slopstopper-triage"
fi

# ── post-install guidance ────────────────────────────────────────────────────

sep
echo ""
echo "  🎉 Skills installed at project level!"
echo ""
echo "  Claude Code auto-discovers the skills under .claude/skills/ for any"
echo "  contributor working in this repo. Commit them alongside the workflows."
echo ""
echo "  Which skill triggers depends on what the prompt asks:"
echo ""
echo "    • \"install / refresh / upgrade slopstopper\" → slopstopper-install"
echo "    • \"fix this failing slopstopper check\"      → slopstopper-triage"
echo ""
echo "  To install the full SlopStopper suite into a fresh repo:"
echo "    cd <your-repo>"
echo "    curl -fsSL ${REPO_RAW}/install.sh | bash"
echo ""
echo "  Re-running this script from inside the repo refreshes the skills to"
echo "  the latest upstream version."
echo ""
sep
