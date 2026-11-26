#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="autoresearch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="global"
TARGET_PROJECT=""
ACTION="install"
COPY_MODE=0
DRY_RUN=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [--global | --project <dir>] [--copy] [--check | --uninstall] [--dry-run]

Install, verify, or remove the self-contained '${SKILL_NAME}' Agent Skill.

Options:
  --global          Target ~/.claude/skills and ~/.agents/skills (default)
  --project <dir>   Target <dir>/.claude/skills and <dir>/.agents/skills
  --copy            Copy standalone skill files instead of creating symlinks
  --check           Verify installed skill files and run self-contained doctor check
  --uninstall       Remove installed skill links/directories at target paths
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
    --copy)
      COPY_MODE=1
      shift
      ;;
    --check)
      ACTION="check"
      shift
      ;;
    --uninstall)
      ACTION="uninstall"
      shift
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
  mkdir -p "${TARGET_PROJECT}"
  PROJECT_ABS="$(cd "${TARGET_PROJECT}" && pwd)"
  TARGETS=(
    "${PROJECT_ABS}/.claude/skills/${SKILL_NAME}"
    "${PROJECT_ABS}/.agents/skills/${SKILL_NAME}"
  )
fi

if [[ "${ACTION}" == "check" ]]; then
  status_code=0
  for dest in "${TARGETS[@]}"; do
    if [[ -f "${dest}/SKILL.md" && -f "${dest}/scripts/autoresearch.py" ]]; then
      echo "OK: ${dest}/SKILL.md"
    else
      echo "MISSING: ${dest}/SKILL.md or scripts/autoresearch.py" >&2
      status_code=1
    fi
  done
  if [[ "${status_code}" -eq 0 ]]; then
    python3 "${TARGETS[0]}/scripts/autoresearch.py" doctor >/dev/null && echo "OK: autoresearch.py doctor passed" || status_code=1
  fi
  exit "${status_code}"
fi

if [[ "${ACTION}" == "uninstall" ]]; then
  for dest in "${TARGETS[@]}"; do
    if [[ -L "${dest}" || -d "${dest}" ]]; then
      if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[dry-run] rm -rf \"${dest}\""
      else
        rm -rf "${dest}"
        echo "Removed: ${dest}"
      fi
    else
      echo "Not installed: ${dest}"
    fi
  done
  exit 0
fi

for dest in "${TARGETS[@]}"; do
  parent="$(dirname "${dest}")"
  if [[ -e "${dest}" && ! -L "${dest}" && "${COPY_MODE}" -eq 0 ]]; then
    echo "Skip (existing non-symlink path; use --copy or --uninstall first): ${dest}" >&2
    continue
  fi
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    if [[ "${COPY_MODE}" -eq 1 ]]; then
      echo "[dry-run] cp -R \"${SKILL_SRC}\" \"${dest}\""
    else
      echo "[dry-run] ln -sfn \"${SKILL_SRC}\" \"${dest}\""
    fi
  else
    mkdir -p "${parent}"
    if [[ "${COPY_MODE}" -eq 1 ]]; then
      rm -rf "${dest}"
      cp -R "${SKILL_SRC}" "${dest}"
      find "${dest}" -name "__pycache__" -type d -prune -exec rm -rf {} +
      echo "Copied: ${SKILL_SRC} -> ${dest}"
    else
      ln -sfn "${SKILL_SRC}" "${dest}"
      echo "Installed: ${dest} -> ${SKILL_SRC}"
    fi
  fi
done
