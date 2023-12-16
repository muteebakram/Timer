#!/bin/bash

help=false
slient=false
kill=false
log=false

cd ~/Desktop/Muteeb/Code/Timer/ || exit
source timer/bin/activate

while getopts ':hskl' flag; do
  case "${flag}" in
    h) help=true ;;
    s) slient=true ;;
    k) kill=true ;;
    l) log=true ;;
    *)
      python3 main.py -h
      exit 1
      ;;
  esac
done

if [ "$help" == true ]; then
  python3 main.py -h || exit 0
fi

if [ "$log" == true ]; then
  tail -f timer.log
  exit 0
fi

if [ "$kill" == true ]; then
  kill $(ps aux | grep 'main.py' | grep -v grep | awk '{print $2}')
  exit 0
fi

if [ "$slient" == true ]; then
  python3 main.py -s &
else
  python3 main.py &
fi

deactivate
cd - || exit
