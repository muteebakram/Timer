#!/bin/bash

PWD=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

help=false
slient=false
kill=false
log=false
print=false
check_status=false

while getopts ':chsklp' flag; do
  case "${flag}" in
    h) help=true ;;
    s) slient=true ;;
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

if [ "$check_status" == true ]; then
  is_running 1
  exit 0
fi

if [ "$kill" == true ]; then
  kill $(ps aux | grep 'main.py' | grep -v grep | awk '{print $2}')
  exit 0
fi

cd "$PWD" || exit

if [ "$log" == true ]; then
  tail -f logs/timer.log
  exit 0
fi

source timer/bin/activate

if [ "$help" == true ]; then
  python3 main.py -h
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

if [ "$slient" == true ]; then
  python3 main.py -s &
else
  python3 main.py &
fi

deactivate
cd - || exit
