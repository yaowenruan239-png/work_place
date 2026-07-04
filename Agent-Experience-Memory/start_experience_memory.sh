#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPP_DIR="$PROJECT_ROOT/cpp_memory_service"
BUILD_DIR="$CPP_DIR/build"
SERVICE_BIN="$BUILD_DIR/agent_memory_service"
LOG_DIR="$PROJECT_ROOT/logs"
SERVICE_LOG="$LOG_DIR/agent_memory_service.log"
PID_FILE="$PROJECT_ROOT/.agent_memory_service.pid"
SERVICE_URL="http://127.0.0.1:8080"

INSTALL_DEPS=0
SEED_DATA=0
REBUILD_CPP=0
SKIP_MYSQL=0

usage() {
  cat <<'USAGE'
Usage: ./start_experience_memory.sh [options]

Options:
  --install-deps   Run pip install -r requirements.txt before startup.
  --seed           Insert demo experience memories before loading the C++ index.
                   Note: current seed_data.py does not de-duplicate rows.
  --rebuild-cpp    Remove cpp_memory_service/build and rebuild C++ service.
  --skip-mysql     Do not run docker compose up -d for MySQL.
  -h, --help       Show this help message.

Examples:
  ./start_experience_memory.sh
  ./start_experience_memory.sh --install-deps --seed
  ./start_experience_memory.sh --rebuild-cpp
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-deps)
      INSTALL_DEPS=1
      shift
      ;;
    --seed)
      SEED_DATA=1
      shift
      ;;
    --rebuild-cpp)
      REBUILD_CPP=1
      shift
      ;;
    --skip-mysql)
      SKIP_MYSQL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

log() {
  printf '[experience-memory] %s\n' "$*"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

health_check() {
  python - <<'PY' >/dev/null 2>&1
from urllib.request import urlopen
urlopen("http://127.0.0.1:8080/health", timeout=1).read()
PY
}

wait_for_http_health() {
  local retries="${1:-30}"
  local delay="${2:-1}"
  for _ in $(seq 1 "$retries"); do
    if health_check; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

wait_for_mysql() {
  log "Waiting for MySQL to be ready..."
  for _ in $(seq 1 60); do
    if python - <<'PY' >/dev/null 2>&1
from python_client.db import fetch_all
fetch_all("SELECT 1 AS ok")
PY
    then
      log "MySQL is ready."
      return 0
    fi
    sleep 2
  done
  echo "MySQL is not ready after waiting. Check docker compose logs." >&2
  exit 1
}

start_mysql() {
  if [[ "$SKIP_MYSQL" -eq 1 ]]; then
    log "Skipping MySQL startup."
    return
  fi

  if ! command_exists docker; then
    echo "docker is required to start MySQL." >&2
    exit 1
  fi

  log "Starting MySQL with docker compose..."
  (cd "$PROJECT_ROOT" && docker compose up -d)
  wait_for_mysql
}

install_deps() {
  if [[ "$INSTALL_DEPS" -eq 1 ]]; then
    log "Installing Python dependencies..."
    (cd "$PROJECT_ROOT" && python -m pip install -r requirements.txt)
  fi
}

seed_data() {
  if [[ "$SEED_DATA" -eq 1 ]]; then
    log "Seeding demo experience memories..."
    (cd "$PROJECT_ROOT" && python -m python_client.seed_data)
  fi
}

build_cpp_service() {
  if ! command_exists cmake; then
    echo "cmake is required to build the C++ memory service." >&2
    exit 1
  fi

  if [[ "$REBUILD_CPP" -eq 1 ]]; then
    log "Removing existing C++ build directory..."
    rm -rf "$BUILD_DIR"
  fi

  if [[ ! -x "$SERVICE_BIN" ]]; then
    log "Building C++ memory service..."
    mkdir -p "$BUILD_DIR"
    (cd "$BUILD_DIR" && cmake .. && cmake --build .)
  else
    log "C++ memory service binary already exists."
  fi
}

start_cpp_service() {
  mkdir -p "$LOG_DIR"

  if health_check; then
    log "C++ memory service is already running at $SERVICE_URL."
    return
  fi

  if [[ -f "$PID_FILE" ]]; then
    local old_pid
    old_pid="$(cat "$PID_FILE" || true)"
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" >/dev/null 2>&1; then
      log "Found existing process pid=$old_pid, waiting for health check..."
      if wait_for_http_health 10 1; then
        return
      fi
      echo "Existing C++ service process is not healthy. Stop it manually or remove $PID_FILE." >&2
      exit 1
    fi
    rm -f "$PID_FILE"
  fi

  log "Starting C++ memory service in background..."
  (cd "$BUILD_DIR" && nohup "$SERVICE_BIN" > "$SERVICE_LOG" 2>&1 & echo $! > "$PID_FILE")

  if ! wait_for_http_health 30 1; then
    echo "C++ memory service failed to become healthy. See log: $SERVICE_LOG" >&2
    exit 1
  fi

  log "C++ memory service is healthy at $SERVICE_URL."
}

load_index() {
  log "Loading MySQL memory vectors into C++ index..."
  (cd "$PROJECT_ROOT" && NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.load_cpp_index)
}

main() {
  log "Project root: $PROJECT_ROOT"
  install_deps
  start_mysql
  seed_data
  build_cpp_service
  start_cpp_service
  load_index
  log "Startup complete. Health endpoint: $SERVICE_URL/health"
  log "Service log: $SERVICE_LOG"
  log "PID file: $PID_FILE"
}

main
