#!/usr/bin/python3

import argparse
import logging
import platform
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import sleep
from typing import Optional, Sequence


# ----------------------------------Configuration--------------------------------
VOLUME = "0.5"
TIME_FMT = "%I:%M:%S %p"
DEFAULT_WORK_DURATION = 900
DEFAULT_BREAK_DURATION = 120

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio"
LOG_DIR = BASE_DIR / "logs"
# ---------------------------------end of Configuration---------------------------


log = logging.getLogger("timer.log")
log.addHandler(logging.NullHandler())


@dataclass
class TimerState:
    break_num: int = 1
    work_start_time: Optional[datetime] = None
    next_work_time: Optional[datetime] = None
    next_break_time: Optional[datetime] = None

    def start_round(self, now: datetime, work_duration: int, break_duration: int) -> None:
        self.work_start_time = now
        self.next_break_time = now + timedelta(seconds=work_duration)
        self.next_work_time = self.next_break_time + timedelta(seconds=break_duration)


def init_logger(log_dir: Path = LOG_DIR) -> logging.Logger:
    log_file = log_dir / "timer.log"
    resolved_log_file = log_file.resolve()

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        for handler in log.handlers:
            is_same_log_file = (
                isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename).resolve() == resolved_log_file
            )
            if is_same_log_file:
                return log

        log_formatter = logging.Formatter("%(levelname)5.5s  %(filename)5s#%(lineno)3s  %(message)s")
        handler = RotatingFileHandler(
            str(log_file),
            mode="a",
            maxBytes=(2 * 1024 * 1024),
            backupCount=4,
        )
        handler.setFormatter(log_formatter)
        handler.setLevel(logging.DEBUG)

        log.setLevel(logging.DEBUG)
        log.addHandler(handler)
        log.debug("Start logging the times")
    except OSError as exc:
        print(f"Failed to create logger: {exc}")

    return log


def positive_int(value: str) -> int:
    try:
        parsed_value = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc

    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")

    return parsed_value


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.authorship = "muteebakram"
    parser.add_argument("-s", "--silent", action="store_true", help="Run in silent mode.")
    parser.add_argument("--slient", dest="silent", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "-n",
        "--notification",
        action="store_true",
        help="Throw 5 second notification before break. Only on MacOS.",
    )
    parser.add_argument(
        "-w",
        "--work-duration",
        type=positive_int,
        default=DEFAULT_WORK_DURATION,
        help="Duration of work in seconds.",
    )
    parser.add_argument(
        "-b",
        "--break-duration",
        type=positive_int,
        default=DEFAULT_BREAK_DURATION,
        help="Duration of break in seconds.",
    )
    return parser.parse_args(argv)


def is_mac(platform_name: str) -> bool:
    return platform_name.lower() == "darwin"


def is_linux(platform_name: str) -> bool:
    return platform_name.lower().startswith("linux")


def is_windows(platform_name: str) -> bool:
    return platform_name.lower() == "windows"


def format_time(value: datetime) -> str:
    return value.strftime(TIME_FMT).lstrip("0")


def format_optional_time(value: Optional[datetime]) -> str:
    if value is None:
        return "N/A"
    return format_time(value)


def get_time(now: Optional[datetime] = None) -> str:
    return format_time(now or datetime.now())


def add_time(seconds: int, now: Optional[datetime] = None) -> str:
    return format_time((now or datetime.now()) + timedelta(seconds=seconds))


def get_todays_date(today: Optional[date] = None) -> str:
    return (today or date.today()).strftime("%A, %d %b %Y")


def get_path() -> str:
    return str(BASE_DIR)


def greet(base_dir: Path = BASE_DIR) -> None:
    motivate_script = base_dir / "motivate" / "motivate" / "motivate.py"

    try:
        result = subprocess.run(
            [sys.executable, str(motivate_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        print(result.stdout)
    except (OSError, subprocess.SubprocessError):
        print("\n******************************************************")
        print("*                                                    *")
        print("*                                                    *")
        print("*   You can do it! Sending lots of energy to you :)  *")
        print("*                                                    *")
        print("*                                                    *")
        print("******************************************************")


def play_sound(sound_file: Path, platform_name: str) -> None:
    sound_path = str(sound_file)

    try:
        if is_mac(platform_name):
            subprocess.run(["afplay", "--volume", VOLUME, sound_path], check=True)
        elif is_linux(platform_name):
            subprocess.Popen(
                ["aplay", "-q", sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif is_windows(platform_name):
            import winsound

            winsound.PlaySound(sound_path, winsound.SND_ASYNC)
    except (OSError, subprocess.SubprocessError, ImportError) as exc:
        log.debug("Failed to play sound %s: %s", sound_path, exc)


def display_sleep(platform_name: str) -> None:
    if not is_mac(platform_name):
        return

    try:
        subprocess.run(["open", "-a", "ScreenSaverEngine"], check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("Failed to start screen saver: %s", exc)


def wakeup(platform_name: str) -> None:
    if not is_mac(platform_name):
        return

    try:
        from pynput.keyboard import Controller, Key

        keyboard = Controller()
        keyboard.press(Key.cmd)
        keyboard.release(Key.cmd)
    except Exception as exc:
        log.debug("Failed to wake display: %s", exc)


def notify(title: str, subtitle: str, platform_name: str, sleep_fn=sleep) -> None:
    if not is_mac(platform_name):
        return

    display_script = """
    on run argv
        display notification "" with title (item 1 of argv) subtitle (item 2 of argv)
    end run
    """
    result = subprocess.run(
        ["osascript", "-e", display_script, title, subtitle],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        log.debug("Failed to display notification: %s", result.stderr.strip())
        return

    # Clearing Notification Center depends on macOS's private accessibility
    # hierarchy, so treat it as best-effort and never stop the timer for it.
    sleep_fn(5)
    clear_script = """
    tell application "System Events"
        tell process "NotificationCenter"
            try
                if not (window "Notification Center" exists) then return
                set alertGroups to groups of first UI element of first scroll area of first group of window "Notification Center"
                repeat with aGroup in alertGroups
                    try
                        perform (first action of aGroup whose name contains "Close")
                    on error
                        try
                            perform (first action of aGroup whose name contains "Clear")
                        end try
                    end try
                end repeat
            end try
        end tell
    end tell
    """
    result = subprocess.run(
        ["osascript", "-e", clear_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        log.debug("Failed to clear notification: %s", result.stderr.strip())


def time_remaining_for_next_break(state: TimerState, now: Optional[datetime] = None) -> str:
    if state.next_break_time is None:
        return "0m 0s"

    remaining = int((state.next_break_time - (now or datetime.now())).total_seconds())
    remaining = max(0, remaining)
    minutes, seconds = divmod(remaining, 60)
    return f"{minutes}m {seconds}s"


def print_stats(state: TimerState) -> None:
    stats = {
        "Date             : ": get_todays_date(),
        "Time             : ": get_time(),
        "# Breaks         : ": state.break_num - 1,
        "Work Start Time  : ": format_optional_time(state.work_start_time),
        "Next Break Time  : ": format_optional_time(state.next_break_time),
        "Time for Break   : ": time_remaining_for_next_break(state),
    }

    for key, value in stats.items():
        print(f"{key}{value}")

    print()


def make_usr_signal_handler(state: TimerState, platform_name: str):
    def usr_signal_handler(sig, frame):
        print_stats(state)
        notify(
            title=f"Timer Work #{state.break_num}",
            subtitle=(
                "Next Break @ "
                f"{format_optional_time(state.next_break_time)} "
                f"({time_remaining_for_next_break(state)})"
            ),
            platform_name=platform_name,
        )

    return usr_signal_handler


def exit_handler(sig, frame) -> None:
    print("\nGood bye. Have a nice day!\n")
    sys.exit(0)


def configure_signals(state: TimerState, platform_name: str) -> None:
    signal.signal(signal.SIGINT, exit_handler)
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, make_usr_signal_handler(state, platform_name))


def run_timer(args: argparse.Namespace, platform_name: str) -> None:
    state = TimerState()
    configure_signals(state, platform_name)

    log.debug("Platform: %s", platform_name)
    log.debug("Timer application path: %s", BASE_DIR)

    greet()
    log.info("Today's date: %s", get_todays_date())

    if args.silent:
        print("Running in silent mode...")
    else:
        play_sound(AUDIO_DIR / "start_timer.wav", platform_name)

    while True:
        state.start_round(datetime.now(), args.work_duration, args.break_duration)

        log.info(
            "Work  # %s, start work %s, end work/next break %s",
            state.break_num,
            format_optional_time(state.work_start_time),
            format_optional_time(state.next_break_time),
        )
        if args.notification and is_mac(platform_name) and args.work_duration > 5:
            sleep(args.work_duration - 5)
            notify(
                title=f"Take Break #{state.break_num}",
                subtitle=f"Resume Work @ {format_optional_time(state.next_work_time)}",
                platform_name=platform_name,
            )
        else:
            sleep(args.work_duration)

        display_sleep(platform_name)
        if not args.silent:
            play_sound(AUDIO_DIR / "take_break.wav", platform_name)

        log.info(
            "Break # %s, start break %s, end break/next work %s",
            state.break_num,
            get_time(),
            format_optional_time(state.next_work_time),
        )
        sleep(args.break_duration)

        wakeup(platform_name)
        if not args.silent:
            play_sound(AUDIO_DIR / "two_mins_up.wav", platform_name)

        state.break_num += 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    init_logger()
    run_timer(args, platform.system())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
