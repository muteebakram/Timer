#!/usr/bin/python3

from time import sleep
from datetime import date, datetime, timedelta
from pynput.keyboard import Key, Controller
from logging.handlers import RotatingFileHandler
import os, sys, signal, argparse, logging, platform, subprocess

# ----------------------------------Configuration--------------------------------
VOLUME = "0.3"
BREAK_NUM = 1
WORK_DURATION = 900
BREAK_DURATION = 120

MAC = False
LINUX = False
WINDOWS = False
# ---------------------------------end of Configuration---------------------------

log = None


def __init_logger():
    global log
    if log is not None:
        log.debug("logger already initialized.")
        return None

    try:
        "log format <data/time:level:filename:line:function:message>"
        log_formatter = logging.Formatter("%(levelname)5.5s  %(filename)5s#%(lineno)3s  %(message)s")

        "Refer the log file path"
        PATH = get_path()
        log_file = os.path.join(PATH, "timer.log")

        "Max size of the log file is 2MB, it rotate if size exceeds"
        handler = RotatingFileHandler(
            log_file,
            mode="a",
            maxBytes=(2 * 1024 * 1024),
            backupCount=4,
            encoding=None,
            delay=0,
        )

        "appy the log format and level"
        handler.setFormatter(log_formatter)
        handler.setLevel(logging.DEBUG)
        log = logging.getLogger("timer.log")
        log.setLevel(logging.DEBUG)

        "apply the settings to the log"
        log.addHandler(handler)
        log.debug("Start logging the times")
        return handler

    except Exception as e:
        log.error("Failed to create logger: %s", str(e))


def exit_handler(sig, frame):
    print("\nGood bye. Have a nice day!\n")
    greet()
    sys.exit(0)


def greet():
    try:
        print(subprocess.check_output("python motivate/motivate/motivate.py", shell=True, stderr=subprocess.DEVNULL).decode())
    except:
        print("\n******************************************************")
        print("*                                                    *")
        print("*                                                    *")
        print("*   You can do it! Sending lots of energy to you :)  *")
        print("*                                                    *")
        print("*                                                    *")
        print("******************************************************")


def get_time():
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    return time


def next_time(seconds):
    now = datetime.now() + timedelta(seconds=seconds)
    time = now.strftime("%H:%M:%S")
    return time


def play_sound(sound_file):
    if MAC:
        subprocess.check_output("afplay --volume " + VOLUME + " {}".format(sound_file), shell=True)
    elif LINUX:
        subprocess.check_output("aplay -q {}&".format(sound_file), shell=True)
    else:
        winsound.PlaySound(sound_file, winsound.SND_ASYNC)


def get_path():
    return os.getcwd()


def display_sleep():
    if MAC:
        # subprocess.check_output("pmset displaysleepnow", shell=True)  # Put system to sleep.
        subprocess.check_output("open -a ScreenSaverEngine", shell=True)


def wakeup():
    if MAC:
        # subprocess.check_output("pmset relative wake 1", shell=True)  # Wakeup the system.
        # log.debug("Waking up.")
        keyboard = Controller()
        key = Key.cmd

        keyboard.press(key)
        keyboard.release(key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--install", action="store_true", help="Install timer application.")
    parser.add_argument("-s", "--slient", action="store_true", help="Run in silent mode.")
    args = vars(parser.parse_args())
    __init_logger()

    platform_name = platform.system()

    if platform_name == "linux" or platform_name == "linux2":
        LINUX = True
    elif platform_name == "darwin" or platform_name == "Darwin":
        MAC = True
    elif platform_name == "win32" or platform_name == "Windows":
        WINDOWS = True
        if not args["slient"]:
            try:
                import winsound
            except Exception as e:
                print("Sound is not supported in windows. Reason: {0}".format(e))
                args["slient"] = True

    log.debug("Platform: {0}, L: {1}, M: {2}, W: {3}".format(platform_name, LINUX, MAC, WINDOWS))
    PATH = get_path()
    AUDIO_PATH = os.path.join(PATH, "audio")

    log.debug("Timer application path: {0}".format(PATH))
    signal.signal(signal.SIGINT, exit_handler)

    if args["install"]:
        try:
            if MAC or LINUX:
                print("Installing pip packages..")
                subprocess.check_output("pip install requirements.txt", shell=True)
                print("Pip install done.")
                print("Installing motivate..")
                subprocess.check_output("rm -rf motivate/", shell=True)
                subprocess.check_output("git clone https://github.com/mubaris/motivate.git", shell=True)
                print("Motivate install done.")

            elif WINDOWS:
                # TODO: Add windows install.
                print("Refer: https://github.com/mubaris/motivate")

        except Exception as e:
            print("Failed to install timer application. Reason: {0}".format(e))

        exit

    greet()

    if args["slient"]:
        print("Running in slient mode...")

    log.info("Today's date: {0}".format(date.today().strftime("%d %b %Y, %A")))
    if not args["slient"]:
        play_sound(os.path.join(AUDIO_PATH, "start_timer.wav"))

    while True:

        log.info("Work number  {0}, start work  {1}, next break {2}".format(BREAK_NUM, get_time(), next_time(WORK_DURATION)))
        sleep(WORK_DURATION)
        log.info("Work number  {0}, end work    {1}, break end  {2}".format(BREAK_NUM, get_time(), next_time(BREAK_DURATION)))
        if not args["slient"]:
            play_sound(os.path.join(AUDIO_PATH, "take_break.wav"))

        display_sleep()

        log.info("Break number {0}, start break {1}, end break  {2}".format(BREAK_NUM, get_time(), next_time(BREAK_DURATION)))
        sleep(BREAK_DURATION)
        log.info("Break number {0}, end break   {1}, next work  {2}".format(BREAK_NUM, get_time(), next_time(WORK_DURATION)))
        if not args["slient"]:
            play_sound(os.path.join(AUDIO_PATH, "two_mins_up.wav"))

        wakeup()
        BREAK_NUM += 1
