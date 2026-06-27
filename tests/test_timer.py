import subprocess
import unittest
from contextlib import redirect_stderr
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import timer


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
