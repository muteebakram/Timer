#!/usr/bin/python3

import argparse
import logging
import platform
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import RLock, Thread
from time import sleep
from typing import Optional, Sequence


# ----------------------------------Configuration--------------------------------
VOLUME = "0.5"
TIME_FMT = "%I:%M:%S %p"
DEFAULT_WORK_DURATION = 1200
DEFAULT_BREAK_DURATION = 300
WORK_PHASE = "work"
BREAK_PHASE = "break"
WORK_ICON = "💻"
BREAK_ICON = "☕️"

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio"
LOG_DIR = BASE_DIR / "logs"
# ---------------------------------end of Configuration---------------------------


log = logging.getLogger("timer.log")
log.addHandler(logging.NullHandler())
_darwin_menu_bar_controller = None


@dataclass(frozen=True)
class TimerSnapshot:
    break_num: int
    phase: Optional[str]
    deadline: Optional[datetime]
    work_start_time: Optional[datetime]
    next_work_time: Optional[datetime]
    next_break_time: Optional[datetime]


@dataclass
class TimerState:
    break_num: int = 1
    phase: Optional[str] = None
    deadline: Optional[datetime] = None
    work_start_time: Optional[datetime] = None
    next_work_time: Optional[datetime] = None
    next_break_time: Optional[datetime] = None
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def start_round(self, now: datetime, work_duration: int, break_duration: int) -> None:
        with self._lock:
            self.phase = WORK_PHASE
            self.work_start_time = now
            self.next_break_time = now + timedelta(seconds=work_duration)
            self.next_work_time = self.next_break_time + timedelta(seconds=break_duration)
            self.deadline = self.next_break_time

    def start_break(self) -> None:
        with self._lock:
            self.phase = BREAK_PHASE
            self.deadline = self.next_work_time

    def finish_break(self) -> None:
        with self._lock:
            self.break_num += 1
            self.phase = None
            self.deadline = None

    def snapshot(self) -> TimerSnapshot:
        with self._lock:
            return TimerSnapshot(
                break_num=self.break_num,
                phase=self.phase,
                deadline=self.deadline,
                work_start_time=self.work_start_time,
                next_work_time=self.next_work_time,
                next_break_time=self.next_break_time,
            )


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


def seconds_remaining(deadline: Optional[datetime], now: Optional[datetime] = None) -> int:
    if deadline is None:
        return 0

    remaining = int((deadline - (now or datetime.now())).total_seconds())
    return max(0, remaining)


def sleep_until(deadline: datetime, sleep_fn=sleep, now_fn=datetime.now) -> None:
    remaining = (deadline - now_fn()).total_seconds()
    if remaining > 0:
        sleep_fn(remaining)


def format_menu_bar_status(
    phase: Optional[str],
    deadline: Optional[datetime],
    now: Optional[datetime] = None,
    blink_colon: bool = True,
) -> str:
    if phase == WORK_PHASE:
        icon = WORK_ICON
    elif phase == BREAK_PHASE:
        icon = BREAK_ICON
    else:
        return ""

    minutes, seconds = divmod(seconds_remaining(deadline, now), 60)
    separator = ":" if blink_colon else " "
    return f"{icon} {minutes}{separator}{seconds:02d}"


def format_menu_bar_snapshot(
    snapshot: TimerSnapshot,
    now: Optional[datetime] = None,
    blink_colon: bool = True,
) -> str:
    return format_menu_bar_status(snapshot.phase, snapshot.deadline, now, blink_colon)


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
    minutes, seconds = divmod(seconds_remaining(state.snapshot().next_break_time, now), 60)
    return f"{minutes}m {seconds}s"


def timer_stats_lines(state: TimerState) -> list[str]:
    snapshot = state.snapshot()
    minutes, seconds = divmod(seconds_remaining(snapshot.next_break_time), 60)
    time_for_break = f"{minutes}m {seconds}s"
    stats = (
        ("Date             : ", get_todays_date()),
        ("Time             : ", get_time()),
        ("# Breaks         : ", snapshot.break_num - 1),
        ("Work Start Time  : ", format_optional_time(snapshot.work_start_time)),
        ("Next Break Time  : ", format_optional_time(snapshot.next_break_time)),
        ("Time for Break   : ", time_for_break),
    )
    return [f"{key}{value}" for key, value in stats]


def print_stats(state: TimerState) -> None:
    for line in timer_stats_lines(state):
        print(line)

    print()


def make_usr_signal_handler(state: TimerState, platform_name: str):
    def usr_signal_handler(sig, frame):
        snapshot = state.snapshot()
        print_stats(state)
        notify(
            title=f"Timer Work #{snapshot.break_num}",
            subtitle=(
                "Next Break @ "
                f"{format_optional_time(snapshot.next_break_time)} "
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


def setup_darwin_menu_bar(state: TimerState):
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyAccessory,
        NSColor,
        NSFont,
        NSFontAttributeName,
        NSForegroundColorAttributeName,
        NSMenu,
        NSMenuItem,
        NSStatusBar,
        NSVariableStatusItemLength,
    )
    from Foundation import NSAttributedString, NSObject, NSTimer

    def menu_status_font():
        if hasattr(NSFont, "monospacedSystemFontOfSize_weight_"):
            return NSFont.monospacedSystemFontOfSize_weight_(13.0, 0.0)
        return NSFont.userFixedPitchFontOfSize_(13.0) or NSFont.menuFontOfSize_(13.0)

    class DarwinMenuBarController(NSObject):
        def updateStatus_(self, timer):
            self.blink_colon = not self.blink_colon
            title = format_menu_bar_snapshot(state.snapshot(), blink_colon=self.blink_colon)
            button = self.status_item.button()
            if button is not None:
                button.setTitle_(title)

        def menuNeedsUpdate_(self, menu):
            menu.removeAllItems()
            for line in timer_stats_lines(state):
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(line, None, "")
                item.setAttributedTitle_(
                    NSAttributedString.alloc().initWithString_attributes_(
                        line,
                        {
                            NSFontAttributeName: self.menu_font,
                            NSForegroundColorAttributeName: NSColor.labelColor(),
                        },
                    )
                )
                item.setEnabled_(True)
                menu.addItem_(item)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    controller = DarwinMenuBarController.alloc().init()
    controller.blink_colon = False
    controller.menu_font = menu_status_font()
    controller.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
    controller.menu = NSMenu.alloc().initWithTitle_("Timer")
    controller.menu.setAutoenablesItems_(False)
    controller.menu.setDelegate_(controller)
    controller.status_item.setMenu_(controller.menu)
    controller.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1.0,
        controller,
        "updateStatus:",
        None,
        True,
    )
    controller.updateStatus_(None)

    global _darwin_menu_bar_controller
    _darwin_menu_bar_controller = controller
    return app


def notify_async(title: str, subtitle: str, platform_name: str) -> None:
    notification_thread = Thread(
        target=notify,
        kwargs={"title": title, "subtitle": subtitle, "platform_name": platform_name},
        daemon=True,
    )
    notification_thread.start()


def run_timer_round(
    args: argparse.Namespace,
    platform_name: str,
    state: TimerState,
    now_fn=datetime.now,
    sleep_fn=sleep,
) -> None:
    state.start_round(now_fn(), args.work_duration, args.break_duration)
    snapshot = state.snapshot()

    log.info(
        "Work  # %s, start work %s, end work/next break %s",
        snapshot.break_num,
        format_optional_time(snapshot.work_start_time),
        format_optional_time(snapshot.next_break_time),
    )
    if args.notification and is_mac(platform_name) and args.work_duration > 5:
        notification_time = snapshot.next_break_time - timedelta(seconds=5)
        sleep_until(notification_time, sleep_fn=sleep_fn, now_fn=now_fn)
        notify_async(
            title=f"Take Break #{snapshot.break_num}",
            subtitle=f"Resume Work @ {format_optional_time(snapshot.next_work_time)}",
            platform_name=platform_name,
        )

    sleep_until(snapshot.next_break_time, sleep_fn=sleep_fn, now_fn=now_fn)
    state.start_break()
    snapshot = state.snapshot()

    log.info(
        "Break # %s, start break %s, end break/next work %s",
        snapshot.break_num,
        get_time(),
        format_optional_time(snapshot.next_work_time),
    )
    display_sleep(platform_name)
    if not args.silent:
        play_sound(AUDIO_DIR / "take_break.wav", platform_name)

    sleep_until(snapshot.next_work_time, sleep_fn=sleep_fn, now_fn=now_fn)
    wakeup(platform_name)
    if not args.silent:
        play_sound(AUDIO_DIR / "two_mins_up.wav", platform_name)

    state.finish_break()


def run_timer_loop(args: argparse.Namespace, platform_name: str, state: TimerState) -> None:
    log.debug("Platform: %s", platform_name)
    log.debug("Timer application path: %s", BASE_DIR)
    log.debug("Timer settings: work=%ss, break=%ss", args.work_duration, args.break_duration)

    greet()
    log.info("Today's date: %s", get_todays_date())

    if args.silent:
        print("Running in silent mode...")
    else:
        play_sound(AUDIO_DIR / "start_timer.wav", platform_name)

    while True:
        run_timer_round(args, platform_name, state)


def run_timer(args: argparse.Namespace, platform_name: str) -> None:
    state = TimerState()
    configure_signals(state, platform_name)

    if is_mac(platform_name):
        app = None
        try:
            app = setup_darwin_menu_bar(state)
        except Exception as exc:
            log.debug("Failed to start Darwin menu bar timer: %s", exc)

        if app is not None:
            timer_thread = Thread(target=run_timer_loop, args=(args, platform_name, state), daemon=True)
            timer_thread.start()
            app.run()
            return

    run_timer_loop(args, platform_name, state)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    init_logger()
    run_timer(args, platform.system())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
