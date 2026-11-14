#!/usr/bin/env bash
# Start/stop/restart the local BYO server (ComfyUI + comfyui-loovie).
#
# Usage:
#   scripts/byo-server.sh start|stop|restart|status|logs
#
# Configuration (environment variables, or a .byo-server.env file at the repo
# root, see .byo-server.env.example):
#   COMFY_DIR      ComfyUI checkout (default: auto-detect the repo's parent,
#                  then ../ComfyUI beside the repo)
#   COMFY_PYTHON   Python interpreter that runs main.py
#                  (default: $COMFY_DIR/.venv/bin/python, then python3)
#   HOST           bind address (default: 0.0.0.0)
#   PORT           port (default: 8188)
#   LOG            log file (default: /tmp/loovie-comfy-$PORT.log)
#   START_TIMEOUT  seconds to wait for /loovie/health (default: 90)
#
# comfyui-loovie is loaded from custom_nodes/loovie. When that is a symlink
# into this repo (the install.sh default), a restart picks up new code.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8188}"
LOG="${LOG:-/tmp/loovie-comfy-${PORT}.log}"
START_TIMEOUT="${START_TIMEOUT:-90}"

# Auto-detect the ComfyUI checkout when COMFY_DIR is not configured:
#   - repo cloned inside ComfyUI (docs/20 layout): <repo>/..
#   - repo cloned beside ComfyUI:                  <repo>/../ComfyUI
if [[ -z "${COMFY_DIR:-}" ]]; then
  for candidate in "$ROOT/.." "$ROOT/../ComfyUI"; do
    if [[ -f "${candidate}/main.py" ]]; then
      COMFY_DIR="$(cd "$candidate" && pwd)"
      break
    fi
  done
fi

if [[ -z "${COMFY_PYTHON:-}" ]]; then
  if [[ -x "${COMFY_DIR}/.venv/bin/python" ]]; then
    COMFY_PYTHON="${COMFY_DIR}/.venv/bin/python"
  else
    COMFY_PYTHON="python3"
  fi
fi

# ComfyUI binds 0.0.0.0/::, so probe loopback for those.
case "$HOST" in
  0.0.0.0|::|"[::]") PROBE_HOST="127.0.0.1" ;;
  *) PROBE_HOST="$HOST" ;;
esac
HEALTH_URL="http://${PROBE_HOST}:${PORT}/loovie/health"

log() { printf '[byo-server] %s\n' "$*"; }
fail() { printf '[byo-server] ERROR: %s\n' "$*" >&2; exit 1; }

pid_on_port() {
  local pid=""
  if command -v ss >/dev/null 2>&1; then
    pid="$(ss -ltnp 2>/dev/null \
      | awk -v port=":${PORT}" '$4 ~ port"$" {print}' \
      | grep -o 'pid=[0-9]*' | head -n1 | cut -d= -f2 || true)"
  fi
  if [[ -z "$pid" ]] && command -v lsof >/dev/null 2>&1; then
    pid="$(lsof -tiTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
  fi
  if [[ -z "$pid" ]]; then
    # Fallback for systems without ss/lsof. Verify argv[1] is main.py so a
    # shell wrapper containing the same command line cannot match.
    local candidate
    while read -r candidate; do
      if [[ -r "/proc/${candidate}/cmdline" ]] \
        && tr '\0' '\n' < "/proc/${candidate}/cmdline" | sed -n '2p' | grep -qx 'main.py'; then
        pid="$candidate"
        break
      fi
    done < <(pgrep -f "main\.py.*--port[ =]${PORT}([^0-9]|$)" 2>/dev/null || true)
  fi
  printf '%s' "$pid"
}

wait_healthy() {
  local pid="$1" waited=0
  while (( waited < START_TIMEOUT )); do
    if ! kill -0 "$pid" 2>/dev/null; then
      log "process exited during startup; last log lines:"
      tail -n 20 "$LOG" >&2 || true
      return 1
    fi
    if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  log "timed out after ${START_TIMEOUT}s waiting for $HEALTH_URL"
  tail -n 20 "$LOG" >&2 || true
  return 1
}

cmd_start() {
  local pid
  pid="$(pid_on_port)"
  if [[ -n "$pid" ]]; then
    log "already running on port ${PORT} (pid ${pid})"
    return 0
  fi
  [[ -f "${COMFY_DIR}/main.py" ]] || fail "ComfyUI not found${COMFY_DIR:+ at COMFY_DIR=${COMFY_DIR}}. Copy .byo-server.env.example to .byo-server.env and set COMFY_DIR, or run with COMFY_DIR=/path/to/ComfyUI."
  command -v "$COMFY_PYTHON" >/dev/null 2>&1 || [[ -x "$COMFY_PYTHON" ]] \
    || fail "Python interpreter not found: ${COMFY_PYTHON}. Set COMFY_PYTHON in .byo-server.env."

  mkdir -p "$(dirname "$LOG")"
  log "starting ComfyUI from ${COMFY_DIR} on ${HOST}:${PORT} (log: ${LOG})"
  pushd "$COMFY_DIR" >/dev/null
  nohup "$COMFY_PYTHON" main.py --listen "$HOST" --port "$PORT" >>"$LOG" 2>&1 &
  pid=$!
  popd >/dev/null
  log "pid ${pid}, waiting for ${HEALTH_URL} ..."
  if wait_healthy "$pid"; then
    log "ready (pid ${pid})"
  else
    fail "server did not become healthy; see ${LOG}"
  fi
}

cmd_stop() {
  local pid
  pid="$(pid_on_port)"
  if [[ -z "$pid" ]]; then
    log "not running on port ${PORT}"
    return 0
  fi
  log "stopping pid ${pid} ..."
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 40); do
    kill -0 "$pid" 2>/dev/null || { log "stopped"; return 0; }
    sleep 0.25
  done
  log "still running, sending SIGKILL"
  kill -9 "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || { log "stopped"; return 0; }
    sleep 0.25
  done
  fail "could not stop pid ${pid}"
}

cmd_status() {
  local pid
  pid="$(pid_on_port)"
  if [[ -z "$pid" ]]; then
    log "not running on port ${PORT}"
    return 1
  fi
  log "running on port ${PORT} (pid ${pid})"
  if curl -fsS --max-time 3 "$HEALTH_URL" 2>/dev/null; then
    printf '\n'
    return 0
  fi
  log "health check failed: ${HEALTH_URL}"
  return 1
}

cmd_logs() {
  [[ -f "$LOG" ]] || fail "no log file at ${LOG}"
  exec tail -n 100 -f "$LOG"
}

case "${1:-}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_stop; cmd_start ;;
  status)  cmd_status ;;
  logs)    cmd_logs ;;
  *)
    sed -n '2,20p' "${BASH_SOURCE[0]}"
    exit 2
    ;;
esac
