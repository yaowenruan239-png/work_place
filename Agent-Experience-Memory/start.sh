#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPP_DIR="$PROJECT_ROOT/cpp_memory_service"
BUILD_DIR="$CPP_DIR/build"
CPP_SERVICE_BIN="$BUILD_DIR/agent_memory_service"
LOG_DIR="$PROJECT_ROOT/logs"

CPP_SERVICE_LOG="$LOG_DIR/agent_memory_service.log"
CPP_PID_FILE="$PROJECT_ROOT/.agent_memory_service.pid"
CPP_SERVICE_URL="http://127.0.0.1:8080"
CPP_SERVICE_PORT="8080"

API_SERVICE_LOG="$LOG_DIR/agent_memory_api.log"
API_PID_FILE="$PROJECT_ROOT/.agent_memory_api.pid"
API_SERVICE_URL="http://127.0.0.1:8090"
API_SERVICE_PORT="8090"
API_START_COMMAND="python -m python_client.api_service"

export NO_PROXY="127.0.0.1,localhost"
export no_proxy="127.0.0.1,localhost"

COMMAND="start"
INSTALL_DEPS=0
SEED_DATA=0
REBUILD_CPP=0
SKIP_MYSQL=0
STOP_MYSQL=0
FORCE_STOP=0

usage() {
  cat <<'USAGE'
Usage: ./start.sh [command] [options]

Commands:
  start       Start MySQL if needed, build/start C++ memory service, load index, then start Python API service. Default command.
  stop        Stop Python API service, then stop C++ memory service. MySQL is kept running unless --stop-mysql is provided.
  status      Show C++ service, Python API service, and MySQL container status.
  restart     Stop both services, then start all services and reload index.

Start options:
  --install-deps   Run pip install -r requirements.txt before startup.
  --seed           Insert demo experience memories before loading the C++ index.
                   Note: current seed_data.py does not de-duplicate rows.
  --rebuild-cpp    Remove cpp_memory_service/build and rebuild C++ service.
  --skip-mysql     Do not run docker compose up -d for MySQL.

Stop options:
  --stop-mysql     Also stop MySQL with docker compose down.
  --force          Use kill -9 if normal stop does not terminate a service.

Common options:
  -h, --help       Show this help message.

Examples:
  ./start.sh
  ./start.sh start --install-deps --seed
  ./start.sh start --rebuild-cpp
  ./start.sh status
  ./start.sh stop
  ./start.sh stop --stop-mysql
  ./start.sh restart
USAGE
}

if [[ $# -gt 0 ]]; then
  case "$1" in
    start|stop|status|restart)
      COMMAND="$1"
      shift
      ;;
  esac
fi

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
    --stop-mysql)
      STOP_MYSQL=1
      shift
      ;;
    --force)
      FORCE_STOP=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option or command: $1" >&2
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
  local url="$1"

  if command_exists curl; then
    curl --noproxy "*" -fsS "$url/health" >/dev/null 2>&1
    return $?
  fi

  NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python - "$url" <<'PY' >/dev/null 2>&1
import sys
from urllib.request import urlopen
urlopen(sys.argv[1] + "/health", timeout=1).read()
PY
}

print_health() {
  local url="$1"

  if command_exists curl; then
    curl --noproxy "*" -fsS "$url/health" 2>/dev/null || true
    printf '\n'
    return
  fi

  NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python - "$url" <<'PY' 2>/dev/null || true
import sys
from urllib.request import urlopen
print(urlopen(sys.argv[1] + "/health", timeout=1).read().decode())
PY
}

wait_for_http_health() {
  local url="$1"
  local retries="${2:-30}"
  local delay="${3:-1}"

  for _ in $(seq 1 "$retries"); do
    if health_check "$url"; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

port_pid() {
  local port="$1"

  if command_exists ss; then
    ss -ltnp 2>/dev/null | grep ":$port " | sed -E 's/.*pid=([0-9]+).*/\1/' | head -n 1 || true
  elif command_exists lsof; then
    lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
  fi
}

pid_file_pid() {
  local pid_file="$1"

  if [[ -f "$pid_file" ]]; then
    tr -d '[:space:]' < "$pid_file" 2>/dev/null || true
  fi
}

is_pid_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
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

stop_mysql() {
  if [[ "$STOP_MYSQL" -eq 1 ]]; then
    if ! command_exists docker; then
      echo "docker is required to stop MySQL." >&2
      exit 1
    fi
    log "Stopping MySQL with docker compose down..."
    (cd "$PROJECT_ROOT" && docker compose down)
  fi
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

  if [[ ! -x "$CPP_SERVICE_BIN" ]]; then
    log "Building C++ memory service..."
    mkdir -p "$BUILD_DIR"
    (cd "$BUILD_DIR" && cmake .. && cmake --build .)
  else
    log "C++ memory service binary already exists."
  fi
}

start_background_service() {
  local name="$1"
  local url="$2"
  local port="$3"
  local pid_file="$4"
  local log_file="$5"
  shift 5
  local command_args=("$@")

  mkdir -p "$LOG_DIR"

  if health_check "$url"; then
    log "$name is already running at $url."
    return
  fi

  local old_pid
  old_pid="$(pid_file_pid "$pid_file")"
  if is_pid_running "$old_pid"; then
    log "Found existing $name process pid=$old_pid, waiting for health check..."
    if wait_for_http_health "$url" 10 1; then
      return
    fi
    echo "Existing $name process is not healthy. Stop it with: ./start.sh stop --force" >&2
    exit 1
  fi
  rm -f "$pid_file"

  local existing_port_pid
  existing_port_pid="$(port_pid "$port")"
  if is_pid_running "$existing_port_pid"; then
    echo "Port $port is already occupied by pid=$existing_port_pid, but $url/health is not healthy." >&2
    echo "Please kill the occupying process first: kill $existing_port_pid" >&2
    exit 1
  fi

  log "Starting $name in background..."
  (
    cd "$PROJECT_ROOT"
    nohup "${command_args[@]}" > "$log_file" 2>&1 &
    echo $! > "$pid_file"
  )

  if ! wait_for_http_health "$url" 30 1; then
    echo "$name failed to become healthy. See log: $log_file" >&2
    exit 1
  fi

  log "$name is healthy at $url."
}

start_cpp_service() {
  start_background_service \
    "C++ Memory Service" \
    "$CPP_SERVICE_URL" \
    "$CPP_SERVICE_PORT" \
    "$CPP_PID_FILE" \
    "$CPP_SERVICE_LOG" \
    "$CPP_SERVICE_BIN"
}

start_api_service() {
  start_background_service \
    "Python API Service" \
    "$API_SERVICE_URL" \
    "$API_SERVICE_PORT" \
    "$API_PID_FILE" \
    "$API_SERVICE_LOG" \
    python -m python_client.api_service
}

load_index() {
  log "Loading MySQL memory vectors into C++ index..."
  (cd "$PROJECT_ROOT" && NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.load_cpp_index)
}

stop_background_service() {
  local name="$1"
  local url="$2"
  local port="$3"
  local pid_file="$4"

  local pid_from_file
  local pid_from_port
  pid_from_file="$(pid_file_pid "$pid_file")"
  pid_from_port="$(port_pid "$port")"

  if [[ -z "$pid_from_file" && -z "$pid_from_port" ]]; then
    log "$name is not running on port $port."
    rm -f "$pid_file"
    return
  fi

  local target_pid="${pid_from_port:-$pid_from_file}"
  if [[ -n "$pid_from_file" && "$pid_from_file" != "$target_pid" ]]; then
    log "$name PID file has pid=$pid_from_file, but port $port is owned by pid=$target_pid. Using port owner."
  fi

  if is_pid_running "$target_pid"; then
    log "Stopping $name pid=$target_pid..."
    kill "$target_pid" >/dev/null 2>&1 || true
    for _ in $(seq 1 10); do
      if ! is_pid_running "$target_pid" && ! health_check "$url"; then
        rm -f "$pid_file"
        log "$name stopped."
        return
      fi
      sleep 1
    done

    if [[ "$FORCE_STOP" -eq 1 ]]; then
      log "Force stopping $name pid=$target_pid..."
      kill -9 "$target_pid" >/dev/null 2>&1 || true
      rm -f "$pid_file"
      log "$name force stopped."
      return
    fi

    echo "$name did not stop in time. Retry with: ./start.sh stop --force" >&2
    exit 1
  fi

  rm -f "$pid_file"
  log "$name process is not running. Removed stale PID file."
}

stop_api_service() {
  stop_background_service "Python API Service" "$API_SERVICE_URL" "$API_SERVICE_PORT" "$API_PID_FILE"
}

stop_cpp_service() {
  stop_background_service "C++ Memory Service" "$CPP_SERVICE_URL" "$CPP_SERVICE_PORT" "$CPP_PID_FILE"
}

print_service_status() {
  local name="$1"
  local url="$2"
  local port="$3"
  local pid_file="$4"
  local log_file="$5"

  echo "$name"
  echo "  URL:          $url"
  echo "  Log:          $log_file"
  echo "  PID file:     $pid_file"

  if health_check "$url"; then
    echo "  Running:      yes"
    echo -n "  Health:       "
    print_health "$url" | sed 's/^/                /'
  else
    echo "  Running:      no or unhealthy"
    echo "  Health:       unavailable"
  fi

  local file_pid
  local listener_pid
  file_pid="$(pid_file_pid "$pid_file")"
  listener_pid="$(port_pid "$port")"
  echo "  PID file PID: ${file_pid:-none}"
  echo "  Port PID:     ${listener_pid:-none}"

  if command_exists ss; then
    echo "  Port listener:"
    ss -ltnp 2>/dev/null | grep ":$port " | sed 's/^/                /' || echo "                no listener on port $port"
  fi
  echo
}

show_status() {
  echo "Project root: $PROJECT_ROOT"
  echo
  print_service_status "C++ Memory Service" "$CPP_SERVICE_URL" "$CPP_SERVICE_PORT" "$CPP_PID_FILE" "$CPP_SERVICE_LOG"
  print_service_status "Python API Service" "$API_SERVICE_URL" "$API_SERVICE_PORT" "$API_PID_FILE" "$API_SERVICE_LOG"

  if command_exists docker; then
    echo "MySQL container:"
    (cd "$PROJECT_ROOT" && docker compose ps mysql) || true
  else
    echo "MySQL container: docker command not found"
  fi
}

start_all() {
  log "Project root: $PROJECT_ROOT"
  install_deps
  start_mysql
  seed_data
  build_cpp_service
  start_cpp_service
  load_index
  start_api_service
  log "Startup complete."
  log "C++ health endpoint: $CPP_SERVICE_URL/health"
  log "Python API health endpoint: $API_SERVICE_URL/health"
  log "C++ service log: $CPP_SERVICE_LOG"
  log "Python API service log: $API_SERVICE_LOG"
  log "C++ PID file: $CPP_PID_FILE"
  log "Python API PID file: $API_PID_FILE"
}

stop_all() {
  stop_api_service
  stop_cpp_service
  stop_mysql
}

restart_all() {
  stop_all
  start_all
}

case "$COMMAND" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  status)
    show_status
    ;;
  restart)
    restart_all
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    usage
    exit 1
    ;;
esac
