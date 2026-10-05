"""Tests for the narrowly scoped Pocket process stop helper.

Every process object in this module is a fake.  The tests must never terminate
the Python process running the test suite or any local ComfyUI process.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import psutil


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend import service_control


class FakeProcess:
    def __init__(
        self,
        *,
        pid: int,
        created: float,
        command: list[str] | None = None,
        cwd: str,
        environment: dict[str, str] | None = None,
        terminate_error: BaseException | None = None,
        wait_error: BaseException | None = None,
    ) -> None:
        self.pid = pid
        self._created = created
        self._command = command or ["python", "-m", "backend.server"]
        self._cwd = cwd
        self._environment = environment or {}
        self.terminate_error = terminate_error
        self.wait_error = wait_error
        self.terminated = False
        self.wait_calls: list[float] = []
        self.children_called = False

    def create_time(self) -> float:
        return self._created

    def cmdline(self) -> list[str]:
        return self._command

    def cwd(self) -> str:
        return self._cwd

    def environ(self) -> dict[str, str]:
        return self._environment

    def terminate(self) -> None:
        if self.terminate_error:
            raise self.terminate_error
        self.terminated = True

    def wait(self, timeout: float) -> None:
        self.wait_calls.append(timeout)
        if self.wait_error:
            raise self.wait_error

    def children(self, recursive: bool = False) -> list[object]:
        self.children_called = True
        raise AssertionError(f"stop_server must not inspect child processes (recursive={recursive})")


def write_record(home: Path, *, pid: int = 4242, created: float = 100.25, cwd: Path | None = None) -> dict:
    record = {
        "pid": pid,
        "created": created,
        "cwd": str((cwd or home).resolve()),
    }
    (home / "pocket-process.json").write_text(json.dumps(record), encoding="utf-8")
    return record


class ServiceControlTest(unittest.TestCase):
    def make_home(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        return directory, Path(directory.name).resolve()

    def test_stop_requires_pid_time_command_cwd_and_home_match(self) -> None:
        directory, home = self.make_home()
        self.addCleanup(directory.cleanup)
        record = write_record(home)
        process = FakeProcess(
            pid=record["pid"],
            created=record["created"],
            cwd=str(home),
            environment={"COMFY_POCKET_HOME": str(home)},
        )

        with patch.object(service_control.psutil, "Process", return_value=process):
            result = service_control.stop_server(home)

        self.assertIn("Pocket stopped", result)
        self.assertTrue(process.terminated)
        self.assertEqual(process.wait_calls, [8])
        self.assertFalse((home / "pocket-process.json").exists())
        self.assertFalse(process.children_called)

    def test_stop_rejects_wrong_home_command_or_cwd_without_terminating(self) -> None:
        cases = (
            {
                "environment": {"COMFY_POCKET_HOME": "wrong-home"},
            },
            {
                "command": ["python", "-m", "other.server"],
                "environment": {},
            },
            {
                "cwd": "wrong-cwd",
                "environment": {},
            },
        )

        for overrides in cases:
            with self.subTest(overrides=overrides):
                directory, home = self.make_home()
                self.addCleanup(directory.cleanup)
                record = write_record(home)
                process = FakeProcess(
                    pid=record["pid"],
                    created=record["created"],
                    cwd=overrides.get("cwd", str(home)),
                    command=overrides.get("command"),
                    environment=overrides.get("environment", {"COMFY_POCKET_HOME": str(home)}),
                )

                with patch.object(service_control.psutil, "Process", return_value=process):
                    with self.assertRaisesRegex(ValueError, "身份不匹配"):
                        service_control.stop_server(home)

                self.assertFalse(process.terminated)
                self.assertTrue((home / "pocket-process.json").exists())
                self.assertFalse(process.children_called)

    def test_pid_reuse_is_not_killed_and_stale_record_is_cleared(self) -> None:
        directory, home = self.make_home()
        self.addCleanup(directory.cleanup)
        record = write_record(home, created=100.25)
        process = FakeProcess(
            pid=record["pid"],
            created=200.75,
            cwd=str(home),
            environment={"COMFY_POCKET_HOME": str(home)},
        )

        with patch.object(service_control.psutil, "Process", return_value=process):
            result = service_control.stop_server(home)

        self.assertIn("already stopped", result)
        self.assertFalse(process.terminated)
        self.assertFalse((home / "pocket-process.json").exists())

    def test_missing_process_is_successfully_cleaned_up_without_kill(self) -> None:
        directory, home = self.make_home()
        self.addCleanup(directory.cleanup)
        write_record(home)

        with patch.object(service_control.psutil, "Process", side_effect=psutil.NoSuchProcess(4242)):
            result = service_control.stop_server(home)

        self.assertIn("Pocket stopped", result)
        self.assertFalse((home / "pocket-process.json").exists())

    def test_timeout_is_reported_and_record_is_preserved(self) -> None:
        directory, home = self.make_home()
        self.addCleanup(directory.cleanup)
        record = write_record(home)
        process = FakeProcess(
            pid=record["pid"],
            created=record["created"],
            cwd=str(home),
            environment={"COMFY_POCKET_HOME": str(home)},
            wait_error=psutil.TimeoutExpired(8),
        )

        with patch.object(service_control.psutil, "Process", return_value=process):
            with self.assertRaisesRegex(ValueError, "尚未退出"):
                service_control.stop_server(home)

        self.assertTrue(process.terminated)
        self.assertTrue((home / "pocket-process.json").exists())

    def test_access_denied_is_not_reported_as_a_successful_stop(self) -> None:
        directory, home = self.make_home()
        self.addCleanup(directory.cleanup)
        record = write_record(home)
        process = FakeProcess(
            pid=record["pid"],
            created=record["created"],
            cwd=str(home),
            environment={"COMFY_POCKET_HOME": str(home)},
            terminate_error=psutil.AccessDenied(record["pid"]),
        )

        with patch.object(service_control.psutil, "Process", return_value=process):
            with self.assertRaises(psutil.AccessDenied):
                service_control.stop_server(home)

        self.assertTrue((home / "pocket-process.json").exists())
        self.assertFalse(process.terminated)

    def test_clear_record_only_removes_an_unchanged_record(self) -> None:
        directory, home = self.make_home()
        self.addCleanup(directory.cleanup)
        record = write_record(home)

        service_control.clear_record(home, {**record, "created": 999.0})
        self.assertTrue((home / "pocket-process.json").exists())

        service_control.clear_record(home, record)
        self.assertFalse((home / "pocket-process.json").exists())


if __name__ == "__main__":
    unittest.main()
