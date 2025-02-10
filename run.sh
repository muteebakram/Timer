#!/bin/bash
# shellcheck source=timer/bin/activate

PWD=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

help=false
install=false
silent=false
kill=false
log=false
print=false
check_status=false

while getopts ':ichsklp' flag; do
  case "${flag}" in
    h) help=true ;;
    i) install=true ;;
    s) silent=true ;;
    k) kill=true ;;
    l) log=true ;;
    p) print=true ;;
    c) check_status=true ;;
    *) help=true ;;
  esac
done

is_running() {
  print=$1
  count=$(ps aux | grep "main.py -s" | wc -l)
  if [ "$count" -gt 1 ]; then
    [ "$print" == 1 ] && printf "online (silent) 😊\n"
    return 0
  fi

  count=$(ps aux | grep "main.py" | wc -l)
  if [ "$count" -gt 1 ]; then
    [ "$print" == 1 ] && printf "online 😊\n"
    return 0
  fi

  [ "$print" == 1 ] && printf "offline 🙃\n"
  return 1 # Not running
}

if [ "$install" == true ]; then
  echo "Installing timer..."
  python3 -m venv timer
  source timer/bin/activate
  pip3 install -r requirements.txt
  mkdir logs && touch timer.log
  deactivate
  echo "Timer application installed."
  exit 0
fi

if [ "$check_status" == true ]; then
  is_running 1
  exit 0
fi

if [ "$kill" == true ]; then
  kill "$(ps aux | grep 'main.py' | grep -v grep | awk '{print $2}')"
  exit 0
fi

cd "$PWD" || exit

if [ "$log" == true ]; then
  tail -f logs/timer.log
  exit 0
fi

source timer/bin/activate

if [ "$help" == true ]; then
  echo "
  usage: run.sh [-h] [-i] [-s] [-n] [-w WORK_DURATION] [-b BREAK_DURATION]

  options:
    -h, --help            show this help message and exit
    -i, --install         Install timer application.
    -s, --slient          Run in silent mode.
    -n, --notification    Throw 5 second notification before break. Only on MacOS.
    -w WORK_DURATION, --work-duration WORK_DURATION
                          Duration of work in seconds.
    -b BREAK_DURATION, --break-duration BREAK_DURATION
                          Duration of break in seconds.
  "
  deactivate
  exit 0
fi

if [ "$print" == true ]; then
  kill -USR1 $(pgrep -f "main.py")
  exit 0
fi

if is_running 0; then
  # echo "Already Running!"
  deactivate
  exit 0
fi

if [ "$silent" == true ]; then
  python3 main.py -s -n &
else
  python3 main.py -n &
fi

deactivate
cd - || exit
