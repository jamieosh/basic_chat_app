#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

HOST="${BCA_HOST:-127.0.0.1}"
PORT="${BCA_PORT:-8000}"
RELOAD=0

APP_HOME="${BASIC_CHAT_APP_HOME:-${BCA_HOME:-${REPO_DIR}}}"
RUNTIME_DIR="${BCA_RUNTIME_DIR:-${APP_HOME}/.runtime}"
PID_FILE="${RUNTIME_DIR}/chat-app.pid"
LOG_FILE="${RUNTIME_DIR}/chat-app.log"
ENV_FILE="${APP_HOME}/.env"

usage() {
  cat <<'USAGE'
Usage: scripts/run.sh <command> [options]

Commands:
  foreground            Run server in the foreground
  start                 Run server in the background
  stop                  Stop background server
  restart               Restart background server
  status                Show background server status
  logs                  Tail background server logs
  config                Show resolved config paths and defaults

Options:
  --host <host>         Bind host (default: BCA_HOST or 127.0.0.1)
  --port <port>         Bind port (default: BCA_PORT or 8000)
  --reload              Enable uvicorn reload mode
  --help                Show help
USAGE
}

log() {
  printf '%s\n' "$*"
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

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    printf '%s' "uv"
    return
  fi
  if [ -x "${HOME}/.local/bin/uv" ]; then
    printf '%s' "${HOME}/.local/bin/uv"
    return
  fi
  die "uv not found. Run scripts/install.sh first."
}

is_running() {
  if [ ! -f "${PID_FILE}" ]; then
    return 1
  fi
  local pid
  pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [ -z "${pid}" ]; then
    return 1
  fi
  kill -0 "${pid}" >/dev/null 2>&1
}

start_server() {
  local uv_bin="$1"
  local cmd=("${uv_bin}" run uvicorn main:app --host "${HOST}" --port "${PORT}")

  if [ "${RELOAD}" -eq 1 ]; then
    cmd+=(--reload)
  fi

  mkdir -p "${RUNTIME_DIR}"

  if is_running; then
    log "Server already running (pid $(cat "${PID_FILE}"))."
    return 0
  fi

  if [ -f "${PID_FILE}" ]; then
    rm -f "${PID_FILE}"
  fi

  (
    cd "${REPO_DIR}"
    nohup "${cmd[@]}" >> "${LOG_FILE}" 2>&1 &
    echo "$!" > "${PID_FILE}"
  )

  sleep 1
  if is_running; then
    log "Server started (pid $(cat "${PID_FILE}"))."
    log "Log file: ${LOG_FILE}"
  else
    die "Server failed to start. Check logs: ${LOG_FILE}"
  fi
}

stop_server() {
  if ! is_running; then
    if [ -f "${PID_FILE}" ]; then
      rm -f "${PID_FILE}"
    fi
    log "Server is not running."
    return 0
  fi

  local pid
  pid="$(cat "${PID_FILE}")"
  kill "${pid}" >/dev/null 2>&1 || true

  local attempt
  for attempt in 1 2 3 4 5; do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      rm -f "${PID_FILE}"
      log "Server stopped."
      return 0
    fi
    sleep 1
  done

  kill -9 "${pid}" >/dev/null 2>&1 || true
  rm -f "${PID_FILE}"
  log "Server stopped (forced)."
}

status_server() {
  if is_running; then
    log "Server is running (pid $(cat "${PID_FILE}"))."
    log "Logs: ${LOG_FILE}"
    return 0
  fi
  if [ -f "${PID_FILE}" ]; then
    log "Server is not running (stale pid file removed)."
    rm -f "${PID_FILE}"
  else
    log "Server is not running."
  fi
  return 1
}

tail_logs() {
  mkdir -p "${RUNTIME_DIR}"
  touch "${LOG_FILE}"
  tail -n 100 -f "${LOG_FILE}"
}

show_config() {
  log "APP_HOME=${APP_HOME}"
  log "REPO_DIR=${REPO_DIR}"
  log "ENV_FILE=${ENV_FILE}"
  log "RUNTIME_DIR=${RUNTIME_DIR}"
  log "PID_FILE=${PID_FILE}"
  log "LOG_FILE=${LOG_FILE}"
  log "HOST=${HOST}"
  log "PORT=${PORT}"
  log "RELOAD=${RELOAD}"
}

if [ "$#" -lt 1 ]; then
  usage
  exit 1
fi

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  usage
  exit 0
fi

COMMAND="$1"
shift

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host)
      [ "$#" -ge 2 ] || die "Missing value for --host"
      HOST="$2"
      shift 2
      ;;
    --port)
      [ "$#" -ge 2 ] || die "Missing value for --port"
      PORT="$2"
      shift 2
      ;;
    --reload)
      RELOAD=1
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

need_cmd nohup
UV_BIN="$(ensure_uv)"

if [ "${RELOAD}" -eq 0 ]; then
  case "${BCA_RELOAD:-0}" in
    1|true|TRUE|yes|YES|on|ON) RELOAD=1 ;;
  esac
fi

case "${COMMAND}" in
  foreground)
    cmd=("${UV_BIN}" run uvicorn main:app --host "${HOST}" --port "${PORT}")
    if [ "${RELOAD}" -eq 1 ]; then
      cmd+=(--reload)
    fi
    cd "${REPO_DIR}"
    exec "${cmd[@]}"
    ;;
  start)
    start_server "${UV_BIN}"
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    start_server "${UV_BIN}"
    ;;
  status)
    status_server
    ;;
  logs)
    tail_logs
    ;;
  config)
    show_config
    ;;
  *)
    die "Unknown command: ${COMMAND}"
    ;;
esac
