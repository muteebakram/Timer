#!/bin/bash

help=false
slient=false
kill=false
log=false
check_status=false

while getopts ':chskl' flag; do
  case "${flag}" in
    h) help=true ;;
    s) slient=true ;;
    k) kill=true ;;
    l) log=true ;;
    c) check_status=true ;;
    *) help=true ;;
  esac
done

if [ "$check_status" == true ]; then
  count=$(ps aux | grep "main.py" | wc -l)
  if [ "$count" -gt 1 ]; then
    printf "online 😊\n"
  else
    printf "offline 🙃\n"
  fi
  exit 0
fi

if [ "$log" == true ]; then
  tail -f timer.log
  exit 0
fi

if [ "$kill" == true ]; then
  kill $(ps aux | grep 'main.py' | grep -v grep | awk '{print $2}')
  exit 0
fi

cd ~/Desktop/Muteeb/Code/Timer/ || exit
source timer/bin/activate

if [ "$help" == true ]; then
  python3 main.py -h
  exit 0
fi

if [ "$slient" == true ]; then
  python3 main.py -s &
else
  python3 main.py &
fi

deactivate
cd - || exit
