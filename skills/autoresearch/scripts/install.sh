#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="autoresearch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="global"
TARGET_PROJECT=""
DRY_RUN=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [--global | --project <dir>] [--dry-run]

Install the '${SKILL_NAME}' Agent Skill via symlinks for Claude Code, Codex, and OpenCode.

Options:
  --global          Install into ~/.claude/skills and ~/.agents/skills (default)
  --project <dir>   Install into <dir>/.claude/skills and <dir>/.agents/skills
  --dry-run         Print planned actions without modifying files
  -h, --help        Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --global)
      MODE="global"
      shift
      ;;
    --project)
      MODE="project"
      TARGET_PROJECT="${2:-}"
      if [[ -z "${TARGET_PROJECT}" ]]; then
        echo "Error: --project requires a directory path" >&2
        exit 2
      fi
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${MODE}" == "global" ]]; then
  TARGETS=(
    "${HOME}/.claude/skills/${SKILL_NAME}"
    "${HOME}/.agents/skills/${SKILL_NAME}"
  )
else
  PROJECT_ABS="$(cd "${TARGET_PROJECT}" && pwd)"
  TARGETS=(
    "${PROJECT_ABS}/.claude/skills/${SKILL_NAME}"
    "${PROJECT_ABS}/.agents/skills/${SKILL_NAME}"
  )
fi

for dest in "${TARGETS[@]}"; do
  parent="$(dirname "${dest}")"
  if [[ -e "${dest}" && ! -L "${dest}" ]]; then
    echo "Skip (existing non-symlink path): ${dest}" >&2
    continue
  fi
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] ln -sfn \"${SKILL_SRC}\" \"${dest}\""
  else
    mkdir -p "${parent}"
    ln -sfn "${SKILL_SRC}" "${dest}"
    echo "Installed: ${dest} -> ${SKILL_SRC}"
  fi
done
