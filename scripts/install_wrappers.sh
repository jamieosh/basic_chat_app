#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_DIR="${DEFAULT_REPO_DIR}"
BIN_DIR="${HOME}/.local/bin"

usage() {
  cat <<'USAGE'
Usage: scripts/install_wrappers.sh [options]

Install global wrapper commands:
  bca-install
  bca-update
  bca-run

Options:
  --repo-dir <path>      Repository directory containing scripts/
  --bin-dir <path>       Destination bin directory (default: ~/.local/bin)
  --help                 Show help
USAGE
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo-dir)
      [ "$#" -ge 2 ] || die "Missing value for --repo-dir"
      REPO_DIR="$2"
      shift 2
      ;;
    --bin-dir)
      [ "$#" -ge 2 ] || die "Missing value for --bin-dir"
      BIN_DIR="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

[ -d "${REPO_DIR}/scripts" ] || die "Missing scripts directory under ${REPO_DIR}"
[ -x "${REPO_DIR}/scripts/install.sh" ] || die "Missing executable install.sh under ${REPO_DIR}/scripts"
[ -x "${REPO_DIR}/scripts/update.sh" ] || die "Missing executable update.sh under ${REPO_DIR}/scripts"
[ -x "${REPO_DIR}/scripts/run.sh" ] || die "Missing executable run.sh under ${REPO_DIR}/scripts"

mkdir -p "${BIN_DIR}"

create_wrapper() {
  local name="$1"
  local target_script="$2"
  local wrapper_path="${BIN_DIR}/${name}"
  local default_home="${REPO_DIR}"

  cat > "${wrapper_path}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

APP_HOME="\${BASIC_CHAT_APP_HOME:-${default_home}}"
TARGET="\${APP_HOME}/scripts/${target_script}"

if [ ! -x "\${TARGET}" ]; then
  printf 'Error: missing executable script: %s\n' "\${TARGET}" >&2
  printf 'Hint: set BASIC_CHAT_APP_HOME to your checkout path.\n' >&2
  exit 1
fi

exec "\${TARGET}" "\$@"
EOF
  chmod +x "${wrapper_path}"
}

create_wrapper "bca-install" "install.sh"
create_wrapper "bca-update" "update.sh"
create_wrapper "bca-run" "run.sh"

printf 'Installed wrappers in %s\n' "${BIN_DIR}"
printf '  - %s/bca-install\n' "${BIN_DIR}"
printf '  - %s/bca-update\n' "${BIN_DIR}"
printf '  - %s/bca-run\n' "${BIN_DIR}"
