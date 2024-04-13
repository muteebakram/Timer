#!/usr/bin/python3

from time import sleep
from datetime import date, datetime, timedelta
from pynput.keyboard import Key, Controller
from logging.handlers import RotatingFileHandler
import os, sys, signal, argparse, logging, platform, subprocess

# ----------------------------------Configuration--------------------------------
VOLUME = "0.2"
BREAK_NUM = 1
WORK_DURATION = 900
BREAK_DURATION = 120
WORK_START_TIME = ""
NEXT_BREAK_TIME = ""

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
        log_file = os.path.join(PATH, "logs", "timer.log")

        "Max size of the log file is 2MB, it rotate if size exceeds"
        handler = RotatingFileHandler(
            log_file,
            mode="a",
            maxBytes=(2 * 1024 * 1024),
            backupCount=4,
            encoding=None,
            delay=0,
        )

        "apply the log format and level"
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


def usr_signal_handler(sig, frame):
    print_stats()


def exit_handler(sig, frame):
    print("\nGood bye. Have a nice day!\n")
    sys.exit(0)


def greet():
    try:
        print(
            subprocess.check_output(
                "python motivate/motivate/motivate.py", shell=True, stderr=subprocess.DEVNULL
            ).decode()
        )
    except Exception:
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


def add_time(seconds):
    now = datetime.now() + timedelta(seconds=seconds)
    time = now.strftime("%H:%M:%S")
    return time


def get_todays_date():
    return date.today().strftime("%A, %d %b %Y")


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


def print_stats():
    stats = {
        "TodaysDate": get_todays_date(),
        "NumberOfBreaks": BREAK_NUM,
        "CurrentTime": datetime.now().strftime("%H:%M:%S"),
        "WorkStartTime": WORK_START_TIME,
        "NextBreakTime": NEXT_BREAK_TIME,
    }

    for key, value in stats.items():
        print(f"{key}: {value}")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--install", action="store_true", help="Install timer application.")
    parser.add_argument("-s", "--slient", action="store_true", help="Run in silent mode.")
    parser.add_argument("-w", "--work-duration", help="Duration of work in seconds.", default=900)
    parser.add_argument("-b", "--break-duration", help="Duration of break in seconds.", default=120)
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
    signal.signal(signal.SIGUSR1, usr_signal_handler)

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

        sys.exit(0)

    if args["work_duration"]:
        try:
            WORK_DURATION = int(args["work_duration"])
        except Exception as e:
            print(f"Failed to read work duration. Reason {e}")

    if args["break_duration"]:
        try:
            BREAK_DURATION = int(args["break_duration"])
        except Exception as e:
            print(f"Failed to read break duration. Reason {e}")

    greet()

    log.info("Today's date: {0}".format(get_todays_date()))

    if args["slient"]:
        print("Running in slient mode...")

    if not args["slient"]:
        play_sound(os.path.join(AUDIO_PATH, "start_timer.wav"))

    # End work time is Next break time & End break time is Next work time.
    while True:
        end_work_time = add_time(WORK_DURATION)
        log.info("Work  # {0}, start work  {1}, end work/next break {2}".format(BREAK_NUM, get_time(), end_work_time))
        sleep(WORK_DURATION)

        display_sleep()
        if not args["slient"]:
            play_sound(os.path.join(AUDIO_PATH, "take_break.wav"))

        end_break_time = add_time(BREAK_DURATION)
        log.info("Break # {0}, start break {1}, end break/next work  {2}".format(BREAK_NUM, get_time(), end_break_time))
        sleep(BREAK_DURATION)

        wakeup()
        if not args["slient"]:
            play_sound(os.path.join(AUDIO_PATH, "two_mins_up.wav"))

        WORK_START_TIME = end_break_time
        NEXT_BREAK_TIME = add_time(WORK_DURATION)
        BREAK_NUM += 1
