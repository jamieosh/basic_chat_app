#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -d "${SCRIPT_REPO_ROOT}/.git" ] && [ -f "${SCRIPT_REPO_ROOT}/pyproject.toml" ]; then
  DEFAULT_INSTALL_DIR="${SCRIPT_REPO_ROOT}"
  DEFAULT_REPO_URL="$(git -C "${SCRIPT_REPO_ROOT}" config --get remote.origin.url || true)"
else
  DEFAULT_INSTALL_DIR="${BASIC_CHAT_APP_HOME:-${HOME}/.local/share/basic_chat_app}"
  DEFAULT_REPO_URL=""
fi

INSTALL_DIR="${BASIC_CHAT_APP_HOME:-${DEFAULT_INSTALL_DIR}}"
BRANCH="main"
REPO_URL="${DEFAULT_REPO_URL}"
SKIP_ENV_PROMPT=0
BIN_DIR="${HOME}/.local/bin"
SKIP_CLI_WRAPPERS=0

usage() {
  cat <<'USAGE'
Usage: scripts/install.sh [options]

Install or refresh this project, then sync dependencies with uv.

Options:
  --install-dir <path>   Install/refresh location (default: BASIC_CHAT_APP_HOME or detected repo)
  --repo-url <url>       Git URL used if install directory is missing
  --branch <name>        Git branch to clone/pull (default: main)
  --skip-env             Skip interactive .env generation
  --bin-dir <path>       Directory for bca-* wrappers (default: ~/.local/bin)
  --skip-cli-wrappers    Skip installing bca-install/bca-update/bca-run wrappers
  --help                 Show help
USAGE
}

log() {
  printf '%s\n' "$*"
}

warn() {
  printf 'Warning: %s\n' "$*" >&2
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  local name="$1"
  if ! command -v "${name}" >/dev/null 2>&1; then
    die "Missing required command: ${name}"
  fi
}

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

prompt_text() {
  local label="$1"
  local default_value="${2:-}"
  local reply=""

  if [ -n "${default_value}" ]; then
    printf '%s [%s]: ' "${label}" "${default_value}"
  else
    printf '%s: ' "${label}"
  fi
  IFS= read -r reply || true

  if [ -n "${reply}" ]; then
    printf '%s' "${reply}"
    return
  fi
  printf '%s' "${default_value}"
}

prompt_secret() {
  local label="$1"
  local required="$2"
  local existing_value="${3:-}"
  local reply=""

  while true; do
    if [ -n "${existing_value}" ]; then
      printf '%s (leave blank to keep current): ' "${label}"
    else
      printf '%s: ' "${label}"
    fi
    IFS= read -r -s reply || true
    printf '\n'

    if [ -z "${reply}" ] && [ -n "${existing_value}" ]; then
      printf '%s' "${existing_value}"
      return
    fi

    if [ "${required}" -eq 1 ] && [ -z "${reply}" ]; then
      warn "This key is required for the selected default harness."
      continue
    fi

    printf '%s' "${reply}"
    return
  done
}

find_python_cmd() {
  local candidate
  for candidate in python3 python; do
    if ! command -v "${candidate}" >/dev/null 2>&1; then
      continue
    fi
    if "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
      printf '%s' "${candidate}"
      return 0
    fi
  done
  return 1
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    printf '%s' "uv"
    return
  fi

  log "uv was not found. Installing uv to ${HOME}/.local/bin ..."
  need_cmd curl
  sh -c "$(curl -LsSf https://astral.sh/uv/install.sh)"

  if command -v uv >/dev/null 2>&1; then
    printf '%s' "uv"
    return
  fi

  if [ -x "${HOME}/.local/bin/uv" ]; then
    printf '%s' "${HOME}/.local/bin/uv"
    return
  fi

  die "uv install failed. Ensure ${HOME}/.local/bin is on PATH, then rerun."
}

is_git_clean() {
  local repo_dir="$1"
  git -C "${repo_dir}" diff --quiet --ignore-submodules -- && \
    git -C "${repo_dir}" diff --cached --quiet --ignore-submodules --
}

get_env_value() {
  local env_file="$1"
  local key="$2"

  if [ ! -f "${env_file}" ]; then
    return 0
  fi

  grep -E "^${key}=" "${env_file}" | head -n 1 | sed -E "s/^${key}=//" || true
}

collect_api_key_vars() {
  local example_file="$1"
  local raw_line=""
  local line=""
  local key=""
  local found=()
  local item=""
  local duplicate=0

  while IFS= read -r raw_line || [ -n "${raw_line}" ]; do
    line="${raw_line#\# }"
    line="${line#\#}"
    case "${line}" in
      *_API_KEY=*)
        key="${line%%=*}"
        duplicate=0
        for item in "${found[@]}"; do
          if [ "${item}" = "${key}" ]; then
            duplicate=1
            break
          fi
        done
        if [ "${duplicate}" -eq 0 ]; then
          found+=("${key}")
        fi
        ;;
    esac
  done < "${example_file}"

  if [ "${#found[@]}" -gt 0 ]; then
    printf '%s\n' "${found[@]}"
  fi
}

configure_env_file() {
  local repo_dir="$1"
  local env_example="${repo_dir}/.env.example"
  local env_file="${repo_dir}/.env"
  local default_harness=""
  local harness=""
  local chat_db_path=""
  local api_keys=()
  local api_key=""
  local provider=""
  local required=0
  local existing_value=""
  local prompt_value=""
  local provider_options=()
  local provider_option=""
  local duplicate=0
  local tmp_env=""
  local i=0
  local values=()
  local existing_harness=""
  local allow_rewrite="n"

  if [ ! -f "${env_example}" ]; then
    warn ".env.example not found; skipping .env setup."
    return
  fi

  if [ -f "${env_file}" ]; then
    printf '.env already exists at %s. Reconfigure it now? [y/N]: ' "${env_file}"
    IFS= read -r allow_rewrite || true
    if [ "$(to_lower "${allow_rewrite}")" != "y" ]; then
      log "Keeping existing .env"
      return
    fi
  fi

  while IFS= read -r api_key || [ -n "${api_key}" ]; do
    if [ -n "${api_key}" ]; then
      api_keys+=("${api_key}")
    fi
  done < <(collect_api_key_vars "${env_example}")

  default_harness="$(grep -E '^DEFAULT_CHAT_HARNESS_KEY=' "${env_example}" | head -n 1 | cut -d= -f2- || true)"
  if [ -z "${default_harness}" ]; then
    default_harness="openai"
  fi

  for api_key in "${api_keys[@]}"; do
    provider="$(to_lower "${api_key%_API_KEY}")"
    duplicate=0
    for provider_option in "${provider_options[@]}"; do
      if [ "${provider_option}" = "${provider}" ]; then
        duplicate=1
        break
      fi
    done
    if [ "${duplicate}" -eq 0 ]; then
      provider_options+=("${provider}")
    fi
  done

  existing_harness="$(get_env_value "${env_file}" "DEFAULT_CHAT_HARNESS_KEY")"
  if [ -n "${existing_harness}" ]; then
    default_harness="${existing_harness}"
  fi

  if [ "${#provider_options[@]}" -gt 0 ]; then
    log "Available harness defaults from .env.example: ${provider_options[*]}"
  fi

  while true; do
    harness="$(prompt_text "DEFAULT_CHAT_HARNESS_KEY" "${default_harness}")"
    if [ -n "${harness}" ]; then
      break
    fi
    warn "DEFAULT_CHAT_HARNESS_KEY cannot be empty."
  done

  values=()
  for api_key in "${api_keys[@]}"; do
    provider="$(to_lower "${api_key%_API_KEY}")"
    required=0
    if [ "${provider}" = "${harness}" ]; then
      required=1
    fi
    existing_value="$(get_env_value "${env_file}" "${api_key}")"
    if [ "${required}" -eq 1 ]; then
      prompt_value="$(prompt_secret "${api_key} (required for ${harness})" 1 "${existing_value}")"
    else
      prompt_value="$(prompt_secret "${api_key} (optional)" 0 "${existing_value}")"
    fi
    values+=("${prompt_value}")
  done

  chat_db_path="$(prompt_text "CHAT_DATABASE_PATH (optional)" "$(get_env_value "${env_file}" "CHAT_DATABASE_PATH")")"

  tmp_env="$(mktemp "${TMPDIR:-/tmp}/basic-chat-env.XXXXXX")"
  umask 077
  {
    printf '# Generated by scripts/install.sh\n'
    printf 'DEFAULT_CHAT_HARNESS_KEY=%s\n' "${harness}"
    printf '\n'
    for ((i = 0; i < ${#api_keys[@]}; i++)); do
      if [ -n "${values[i]}" ]; then
        printf '%s=%s\n' "${api_keys[i]}" "${values[i]}"
      else
        printf '# %s=\n' "${api_keys[i]}"
      fi
    done
    if [ -n "${chat_db_path}" ]; then
      printf '\nCHAT_DATABASE_PATH=%s\n' "${chat_db_path}"
    fi
  } > "${tmp_env}"
  mv "${tmp_env}" "${env_file}"
  chmod 600 "${env_file}" || true
  log "Wrote ${env_file}"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --install-dir)
      [ "$#" -ge 2 ] || die "Missing value for --install-dir"
      INSTALL_DIR="$2"
      shift 2
      ;;
    --repo-url)
      [ "$#" -ge 2 ] || die "Missing value for --repo-url"
      REPO_URL="$2"
      shift 2
      ;;
    --branch)
      [ "$#" -ge 2 ] || die "Missing value for --branch"
      BRANCH="$2"
      shift 2
      ;;
    --skip-env)
      SKIP_ENV_PROMPT=1
      shift
      ;;
    --bin-dir)
      [ "$#" -ge 2 ] || die "Missing value for --bin-dir"
      BIN_DIR="$2"
      shift 2
      ;;
    --skip-cli-wrappers)
      SKIP_CLI_WRAPPERS=1
      shift
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

need_cmd git

PYTHON_CMD="$(find_python_cmd || true)"
if [ -z "${PYTHON_CMD}" ]; then
  die "Python 3.11+ is required. Install it first, then rerun."
fi
log "Using Python command: ${PYTHON_CMD}"

if [ -d "${INSTALL_DIR}" ] && [ ! -d "${INSTALL_DIR}/.git" ]; then
  die "Install directory exists but is not a git repository: ${INSTALL_DIR}"
fi

if [ ! -d "${INSTALL_DIR}/.git" ]; then
  [ -n "${REPO_URL}" ] || die "Install directory is missing. Provide --repo-url to clone it."
  mkdir -p "$(dirname "${INSTALL_DIR}")"
  log "Cloning ${REPO_URL} into ${INSTALL_DIR}"
  git clone --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
else
  log "Using existing repository at ${INSTALL_DIR}"
  if ! is_git_clean "${INSTALL_DIR}"; then
    warn "Repository has local changes; skipping git pull."
  else
    log "Pulling latest ${BRANCH} with fast-forward only"
    git -C "${INSTALL_DIR}" fetch --prune origin
    if git -C "${INSTALL_DIR}" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
      git -C "${INSTALL_DIR}" switch "${BRANCH}" >/dev/null
    else
      git -C "${INSTALL_DIR}" switch -c "${BRANCH}" "origin/${BRANCH}" >/dev/null
    fi
    git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
  fi
fi

UV_BIN="$(ensure_uv)"
log "Using uv command: ${UV_BIN}"

(cd "${INSTALL_DIR}" && "${UV_BIN}" sync --frozen)

if [ "${SKIP_ENV_PROMPT}" -eq 0 ]; then
  configure_env_file "${INSTALL_DIR}"
else
  log "Skipping .env setup (--skip-env)"
fi

if [ "${SKIP_CLI_WRAPPERS}" -eq 0 ]; then
  "${INSTALL_DIR}/scripts/install_wrappers.sh" --repo-dir "${INSTALL_DIR}" --bin-dir "${BIN_DIR}"
  case ":${PATH}:" in
    *":${BIN_DIR}:"*) ;;
    *) warn "${BIN_DIR} is not on PATH in this shell. Use full path or add it before using bca-* commands." ;;
  esac
else
  log "Skipping bca-* wrapper install (--skip-cli-wrappers)"
fi

log "Install complete."
log "Run the app with:"
if [ "${SKIP_CLI_WRAPPERS}" -eq 0 ]; then
  log "  bca-run foreground --reload"
  log "Run in background with:"
  log "  bca-run start"
  log "Update with:"
  log "  bca-update"
else
  log "  cd ${INSTALL_DIR} && ./scripts/run.sh foreground --reload"
  log "Run in background with:"
  log "  cd ${INSTALL_DIR} && ./scripts/run.sh start"
fi
