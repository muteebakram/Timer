#!/usr/bin/ python3

import logging
import platform
from os import system
from time import sleep
from datetime import date, datetime
from logging.handlers import RotatingFileHandler

# ----------------------------------Configuration--------------------------------
VOLUME = "6"
BREAK_NUM = 1
WORK_DURATION = 900
BREAK_DURATION = 120

MAC = False
LINUX = False
WINDOWS = False

LINUX_PATH = ""
MAC_PATH = "/Users/mutnawaz/Desktop/Muteeb/Code/timer/"
WINDOWS_PATH = "C:\\Users\\Muteeb\\Desktop\\RV Major Project\\Personal\\timer\\"

# ---------------------------------End of Configuration---------------------------

log = None

if platform.system() == "linux" or platform.system() == "linux2":
    LINUX = True
elif platform.system() == "darwin":
    MAC = True
elif platform.system() == "win32" or platform.system() == "Windows":
    try:
        import winsound
    except Exception as e:
        print("Windows is not supoorted: " + str(e))
        exit(1)
    WINDOWS = True


def __init_logger():

    global log

    if log is not None:
        log.debug("logger already initialized.")
        return None

    try:
        "log format <data/time:level:filename:line:function:message>"
        log_formatter = logging.Formatter(
            "%(levelname)s:%(filename)s:%(lineno)s: %(message)s"
        )

        "refer the log file path"
        PATH = get_path()
        log_file = PATH + "timer.log"

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


def get_time():

    now = datetime.now()
    time = now.strftime("%H:%M")

    return time


def play_sound(sound_file):

    if MAC:
        system("afplay --volume " + VOLUME + " {}".format(sound_file))
    elif LINUX:
        system("aplay -q {}&".format(sound_file))
    else:
        winsound.PlaySound(sound_file, winsound.SND_ASYNC)


def get_path():

    if MAC:
        return MAC_PATH
    elif LINUX:
        return LINUX_PATH
    else:
        return WINDOWS_PATH


if __name__ == "__main__":

    __init_logger()
    PATH = get_path()
    
    log.info("Date : " + str(date.today()))
    play_sound(PATH + "start_timer.wav")

    while True:

        log.info(
            "Work Number  : " + str(BREAK_NUM) + "  Start Time : " + str(get_time())
        )

        sleep(WORK_DURATION)

        log.info(
            "Work Number  : "
            + str(BREAK_NUM)
            + "  End Time   : "
            + str(get_time())
            + "\n"
        )

        play_sound(PATH + "take_break.wav")

        log.info(
            "Break Number : " + str(BREAK_NUM) + "  Start Time : " + str(get_time())
        )
        # system("pmset displaysleepnow")

        sleep(BREAK_DURATION)

        log.info(
            "Break Number : "
            + str(BREAK_NUM)
            + "  End Time   : "
            + str(get_time())
            + "\n"
        )

        play_sound(PATH + "two_mins_up.wav")

        BREAK_NUM += 1
