#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPT="${SCRIPT_DIR}/install.sh"

REFRESH_ENV=0
PASSTHROUGH_ARGS=()

usage() {
  cat <<'USAGE'
Usage: scripts/update.sh [options]

Fast-forward pull and dependency sync for an existing install.

Options:
  --refresh-env         Re-run interactive .env prompts
  --install-dir <path>  Override install location (same as install.sh)
  --branch <name>       Branch to update (default: main)
  --repo-url <url>      Optional fallback clone URL if install dir is missing
  --help                Show help
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --refresh-env)
      REFRESH_ENV=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      PASSTHROUGH_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ ! -x "${INSTALL_SCRIPT}" ]; then
  printf 'Error: missing install helper at %s\n' "${INSTALL_SCRIPT}" >&2
  exit 1
fi

if [ "${REFRESH_ENV}" -eq 1 ]; then
  exec "${INSTALL_SCRIPT}" "${PASSTHROUGH_ARGS[@]}"
fi

exec "${INSTALL_SCRIPT}" --skip-env "${PASSTHROUGH_ARGS[@]}"
