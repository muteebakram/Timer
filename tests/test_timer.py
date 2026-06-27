import subprocess
import unittest
from argparse import Namespace
from contextlib import redirect_stderr
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import timer


class FakeClock:
    def __init__(self, now):
        self.current = now
        self.sleeps = []

    def now(self):
        return self.current

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.current += timedelta(seconds=seconds)


class TimerArgumentTests(unittest.TestCase):
    def test_parse_args_accepts_silent_aliases(self):
        self.assertTrue(timer.parse_args(["--silent"]).silent)
        self.assertTrue(timer.parse_args(["--slient"]).silent)

    def test_parse_args_validates_positive_durations(self):
        args = timer.parse_args(["--work-duration", "60", "--break-duration", "15"])

        self.assertEqual(args.work_duration, 60)
        self.assertEqual(args.break_duration, 15)

        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                timer.parse_args(["--work-duration", "0"])


class TimerStateTests(unittest.TestCase):
    def test_time_remaining_across_midnight(self):
        state = timer.TimerState()
        state.start_round(
            now=datetime(2026, 1, 1, 23, 59, 30),
            work_duration=90,
            break_duration=120,
        )

        self.assertEqual(state.next_break_time, datetime(2026, 1, 2, 0, 1, 0))
        self.assertEqual(
            timer.time_remaining_for_next_break(state, now=datetime(2026, 1, 1, 23, 59, 45)),
            "1m 15s",
        )

    def test_get_path_uses_script_directory(self):
        self.assertEqual(Path(timer.get_path()), Path(timer.__file__).resolve().parent)

    def test_phase_snapshots_follow_timer_round(self):
        state = timer.TimerState()
        now = datetime(2026, 1, 1, 10, 0, 0)

        state.start_round(now=now, work_duration=90, break_duration=20)
        work_snapshot = state.snapshot()

        self.assertEqual(work_snapshot.phase, timer.WORK_PHASE)
        self.assertEqual(work_snapshot.break_num, 1)
        self.assertEqual(work_snapshot.deadline, datetime(2026, 1, 1, 10, 1, 30))

        state.start_break()
        break_snapshot = state.snapshot()

        self.assertEqual(break_snapshot.phase, timer.BREAK_PHASE)
        self.assertEqual(break_snapshot.break_num, 1)
        self.assertEqual(break_snapshot.deadline, datetime(2026, 1, 1, 10, 1, 50))

        state.finish_break()
        finished_snapshot = state.snapshot()

        self.assertEqual(finished_snapshot.break_num, 2)
        self.assertIsNone(finished_snapshot.phase)
        self.assertIsNone(finished_snapshot.deadline)

    def test_sleep_until_ignores_elapsed_deadline(self):
        clock = FakeClock(datetime(2026, 1, 1, 10, 0, 0))

        timer.sleep_until(
            datetime(2026, 1, 1, 9, 59, 59),
            sleep_fn=clock.sleep,
            now_fn=clock.now,
        )

        self.assertEqual(clock.sleeps, [])
        self.assertEqual(clock.now(), datetime(2026, 1, 1, 10, 0, 0))

    def test_sleep_until_sleeps_remaining_seconds(self):
        clock = FakeClock(datetime(2026, 1, 1, 10, 0, 0))

        timer.sleep_until(
            datetime(2026, 1, 1, 10, 0, 12),
            sleep_fn=clock.sleep,
            now_fn=clock.now,
        )

        self.assertEqual(clock.sleeps, [12.0])
        self.assertEqual(clock.now(), datetime(2026, 1, 1, 10, 0, 12))

    def test_round_uses_absolute_work_and_break_deadlines(self):
        clock = FakeClock(datetime(2026, 1, 1, 10, 0, 0))
        state = timer.TimerState()
        args = Namespace(silent=True, notification=False, work_duration=30, break_duration=10)
        transitions = []
        original_start_break = state.start_break
        original_finish_break = state.finish_break

        def recording_start_break():
            before = state.snapshot()
            original_start_break()
            after = state.snapshot()
            transitions.append(("break", clock.now(), before, after))

        def recording_finish_break():
            before = state.snapshot()
            original_finish_break()
            after = state.snapshot()
            transitions.append(("finish", clock.now(), before, after))

        state.start_break = recording_start_break
        state.finish_break = recording_finish_break

        timer.run_timer_round(
            args,
            "Linux",
            state,
            now_fn=clock.now,
            sleep_fn=clock.sleep,
        )

        break_transition = transitions[0]
        finish_transition = transitions[1]

        self.assertEqual(clock.sleeps, [30.0, 10.0])
        self.assertEqual(break_transition[0], "break")
        self.assertEqual(break_transition[1], datetime(2026, 1, 1, 10, 0, 30))
        self.assertEqual(break_transition[2].phase, timer.WORK_PHASE)
        self.assertEqual(break_transition[3].phase, timer.BREAK_PHASE)
        self.assertEqual(break_transition[3].deadline, datetime(2026, 1, 1, 10, 0, 40))
        self.assertEqual(finish_transition[0], "finish")
        self.assertEqual(finish_transition[1], datetime(2026, 1, 1, 10, 0, 40))
        self.assertEqual(finish_transition[2].phase, timer.BREAK_PHASE)
        self.assertEqual(finish_transition[3].break_num, 2)
        self.assertIsNone(finish_transition[3].phase)


class MenuBarStatusTests(unittest.TestCase):
    def test_formats_work_status_with_visible_colon(self):
        self.assertEqual(
            timer.format_menu_bar_status(
                timer.WORK_PHASE,
                datetime(2026, 1, 1, 10, 12, 13),
                now=datetime(2026, 1, 1, 10, 0, 0),
                blink_colon=True,
            ),
            "💻 12:13",
        )

    def test_formats_work_status_with_hidden_colon(self):
        self.assertEqual(
            timer.format_menu_bar_status(
                timer.WORK_PHASE,
                datetime(2026, 1, 1, 10, 12, 13),
                now=datetime(2026, 1, 1, 10, 0, 0),
                blink_colon=False,
            ),
            "💻 12 13",
        )

    def test_formats_break_status_with_visible_colon(self):
        self.assertEqual(
            timer.format_menu_bar_status(
                timer.BREAK_PHASE,
                datetime(2026, 1, 1, 10, 0, 5),
                now=datetime(2026, 1, 1, 10, 0, 0),
                blink_colon=True,
            ),
            "☕️ 0:05",
        )

    def test_formats_expired_break_status(self):
        self.assertEqual(
            timer.format_menu_bar_status(
                timer.BREAK_PHASE,
                datetime(2026, 1, 1, 9, 59, 59),
                now=datetime(2026, 1, 1, 10, 0, 0),
                blink_colon=True,
            ),
            "☕️ 0:00",
        )


class PlatformCommandTests(unittest.TestCase):
    @patch("timer.subprocess.run")
    def test_play_sound_mac_uses_argument_list(self, run_mock):
        timer.play_sound(Path("/tmp/audio with spaces.wav"), "Darwin")

        run_mock.assert_called_once()
        command = run_mock.call_args.args[0]
        kwargs = run_mock.call_args.kwargs

        self.assertEqual(command, ["afplay", "--volume", timer.VOLUME, "/tmp/audio with spaces.wav"])
        self.assertNotIn("shell", kwargs)
        self.assertTrue(kwargs["check"])

    @patch("timer.subprocess.run")
    def test_display_sleep_mac_uses_argument_list(self, run_mock):
        timer.display_sleep("Darwin")

        run_mock.assert_called_once_with(["open", "-a", "ScreenSaverEngine"], check=True)

    @patch("timer.subprocess.run")
    def test_notify_mac_uses_argument_lists(self, run_mock):
        run_mock.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stderr=""),
        ]

        timer.notify("Take Break", "Resume Work", "Darwin", sleep_fn=lambda seconds: None)

        self.assertEqual(run_mock.call_count, 2)
        display_command = run_mock.call_args_list[0].args[0]
        clear_command = run_mock.call_args_list[1].args[0]

        self.assertEqual(display_command[0:2], ["osascript", "-e"])
        self.assertIn("Take Break", display_command)
        self.assertIn("Resume Work", display_command)
        self.assertEqual(clear_command[0:2], ["osascript", "-e"])
        self.assertNotIn("shell", run_mock.call_args_list[0].kwargs)
        self.assertNotIn("shell", run_mock.call_args_list[1].kwargs)


if __name__ == "__main__":
    unittest.main()
