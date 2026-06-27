#!/bin/bash
# shellcheck source=/dev/null

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/timer.log"
PID_FILE="${LOG_DIR}/timer.pid"
VENV_DIR="${SCRIPT_DIR}/.venv"

help=false
install=false
silent=false
kill_timer=false
show_log=false
print_stats=false
check_status=false
run_tests=false
notification=true
work_duration=
break_duration=

usage() {
  cat <<'EOF'
usage: run.sh [options]

options:
  -h, --help             show this help message and exit
  -i, --install          install timer application dependencies
  -s, --silent           run in silent mode
  -n, --notification     enable macOS notification before break (default)
      --no-notification  disable macOS notification before break
  -w, --work-duration    duration of work in seconds
  -b, --break-duration   duration of break in seconds
  -c, --check-status     print whether the timer is running
  -k, --kill             stop the running timer
  -l, --log              follow the timer log
  -p, --print            print current timer stats
  -t, --test             run the test suite
EOF
}

ensure_log_dir() {
  mkdir -p "${LOG_DIR}"
}

require_venv() {
  if [ ! -f "${VENV_DIR}/bin/activate" ]; then
    printf "Timer is not installed. Run ./run.sh --install first.\n" >&2
    exit 1
  fi
}

read_timer_pid() {
  if [ ! -f "${PID_FILE}" ]; then
    return 1
  fi

  local pid
  pid=$(cat "${PID_FILE}")
  if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" 2>/dev/null; then
    printf "%s" "${pid}"
    return 0
  fi

  rm -f "${PID_FILE}"
  return 1
}

is_running() {
  local print_status=${1}
  local pid

  if pid=$(read_timer_pid); then
    if [ "${print_status}" == 1 ]; then
      if ps -p "${pid}" -o command= | grep -q -- "--silent"; then
        printf "online (silent) 😊\n"
      else
        printf "online 😊\n"
      fi
    fi
    return 0
  fi

  [ "${print_status}" == 1 ] && printf "offline 🙃\n"
  return 1
}

while [[ ${#} -gt 0 ]]; do
  case "${1}" in
    -h|--help) help=true ;;
    -i|--install) install=true ;;
    -s|--silent) silent=true ;;
    -k|--kill) kill_timer=true ;;
    -l|--log) show_log=true ;;
    -p|--print) print_stats=true ;;
    -c|--check-status) check_status=true ;;
    -t|--test) run_tests=true ;;
    -n|--notification) notification=true ;;
    --no-notification) notification=false ;;
    -w|--work-duration)
      if [ -z "${2:-}" ]; then
        printf "Missing value for %s\n" "${1}" >&2
        help=true
        break
      fi
      work_duration="${2}"
      shift
      ;;
    --work-duration=*) work_duration="${1#*=}" ;;
    -b|--break-duration)
      if [ -z "${2:-}" ]; then
        printf "Missing value for %s\n" "${1}" >&2
        help=true
        break
      fi
      break_duration="${2}"
      shift
      ;;
    --break-duration=*) break_duration="${1#*=}" ;;
    *)
      printf "Unknown option: %s\n" "${1}" >&2
      help=true
      ;;
  esac
  shift
done

cd "${SCRIPT_DIR}"

if [ "${help}" == true ]; then
  usage
  exit 0
fi

if [ "${install}" == true ]; then
  printf "Installing timer...\n"
  python3 -m venv "${VENV_DIR}"
  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"
  python3 -m pip install --upgrade pip setuptools wheel
  python3 -m pip install -r requirements.txt
  deactivate
  ensure_log_dir
  touch "${LOG_FILE}"
  printf "Timer application installed @ %s\n" "${VENV_DIR}"
  exit 0
fi

ensure_log_dir

if [ "${run_tests}" == true ]; then
  if [ -f "${VENV_DIR}/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "${VENV_DIR}/bin/activate"
    python3 -B -m unittest discover -s tests
    deactivate
  else
    python3 -B -m unittest discover -s tests
  fi
  exit 0
fi

if [ "${check_status}" == true ]; then
  is_running 1 || true
  exit 0
fi

if [ "${kill_timer}" == true ]; then
  if pid=$(read_timer_pid); then
    kill "${pid}" 2>/dev/null || true
    rm -f "${PID_FILE}"
  fi
  exit 0
fi

if [ "${show_log}" == true ]; then
  touch "${LOG_FILE}"
  tail -f "${LOG_FILE}"
  exit 0
fi

if [ "${print_stats}" == true ]; then
  if pid=$(read_timer_pid); then
    kill -USR1 "${pid}"
  else
    printf "Timer is not running.\n" >&2
    exit 1
  fi
  exit 0
fi

if is_running 0; then
  exit 0
fi

require_venv
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

timer_args=()

if [ "${notification}" == true ]; then
  timer_args+=(--notification)
fi

if [ "${silent}" == true ]; then
  timer_args+=(--silent)
fi

if [ -n "${work_duration}" ]; then
  timer_args+=(--work-duration "${work_duration}")
fi

if [ -n "${break_duration}" ]; then
  timer_args+=(--break-duration "${break_duration}")
fi

python3 timer.py "${timer_args[@]}" >>"${LOG_FILE}" 2>&1 &
timer_pid=${!}
printf "%s\n" "${timer_pid}" >"${PID_FILE}"

deactivate
