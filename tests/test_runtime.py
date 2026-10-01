"""Tests for the managed ComfyUI process controller.

The controller is deliberately narrow: it may operate only on the exact
Python command declared in ``config.json``.  These tests keep the process
boundary mocked so a test run can never terminate a real ComfyUI instance.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.runtime import Runtime, is_managed_command


def runtime_settings(tmp_dir: str | None = None) -> dict:
    """Return a command shape equivalent to the local ComfyUI config."""

    cwd = tmp_dir or r"E:\ExampleEngine"
    executable = r"E:\ExampleEngine\.venv\Scripts\python.exe"
    return {
        "cwd": cwd,
        "executable": executable,
        "args": [
            "-s",
            r"E:\ExampleEngine\main.py",
            "--listen",
            "127.0.0.1",
            "--port",
            "8188",
        ],
    }


def full_config(tmp_dir: str | None = None) -> dict:
    return {
        "comfy_url": "http://127.0.0.1:8188",
        "runtime": runtime_settings(tmp_dir),
    }


def managed_command(*, slash: str = "\\", case: str = "same") -> list[str]:
    values = [
        rf"E:{slash}ExampleEngine{slash}.venv{slash}Scripts{slash}python.exe",
        "-s",
        rf"E:{slash}ExampleEngine{slash}main.py",
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
    ]
    if case == "upper":
        return [value.upper() if index in (0, 2) else value for index, value in enumerate(values)]
    if case == "lower":
        return [value.lower() if index in (0, 2) else value for index, value in enumerate(values)]
    return values


class ManagedCommandTest(unittest.TestCase):
    def test_accepts_same_command_with_mixed_path_separators_and_case(self) -> None:
        config = runtime_settings()

        self.assertTrue(
            is_managed_command(
                managed_command(slash="/", case="upper"),
                r"e:/EXAMPLEENGINE",
                config,
            )
        )

    def test_accepts_relative_executable_when_process_cwd_is_configured_cwd(self) -> None:
        config = runtime_settings()

        self.assertTrue(
            is_managed_command(
                [
                    r".venv\Scripts\python.exe",
                    "-s",
                    r"E:\ExampleEngine\main.py",
                    "--listen",
                    "127.0.0.1",
                    "--port",
                    "8188",
                ],
                r"E:\ExampleEngine",
                config,
            )
        )

    def test_rejects_wrong_main_script(self) -> None:
        command = managed_command()
        command[2] = r"E:\ExampleEngine\other.py"

        self.assertFalse(is_managed_command(command, r"E:\ExampleEngine", runtime_settings()))

    def test_rejects_wrong_port(self) -> None:
        command = managed_command()
        command[-1] = "8199"

        self.assertFalse(is_managed_command(command, r"E:\ExampleEngine", runtime_settings()))

    def test_rejects_extra_arguments(self) -> None:
        command = managed_command() + ["--preview-method", "auto"]

        self.assertFalse(is_managed_command(command, r"E:\ExampleEngine", runtime_settings()))

    def test_rejects_different_python_executable(self) -> None:
        command = managed_command()
        command[0] = r"E:\Python312\python.exe"

        self.assertFalse(is_managed_command(command, r"E:\ExampleEngine", runtime_settings()))

    def test_rejects_different_python_script_even_when_other_args_match(self) -> None:
        command = managed_command()
        command[0] = r"E:\ExampleEngine\.venv\Scripts\pythonw.exe"

        self.assertFalse(is_managed_command(command, r"E:\ExampleEngine", runtime_settings()))

    def test_rejects_missing_or_malformed_command(self) -> None:
        config = runtime_settings()

        for command in (None, [], [managed_command()[0]], "not-an-argv"):
            with self.subTest(command=command):
                self.assertFalse(is_managed_command(command, r"E:\ExampleEngine", config))


class _FakeResponse:
    def __init__(self, status: int = 200, payload: dict | None = None) -> None:
        self.status = status
        self.payload = payload or {"system": {}, "devices": []}

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def json(self) -> dict:
        return self.payload


class _FakeClient:
    def __init__(self, *, health_status: int = 200, queue: dict | None = None) -> None:
        self.health_status = health_status
        self.queue = queue or {"queue_running": [], "queue_pending": []}
        self.urls: list[str] = []

    def get(self, url: str, **_kwargs: object) -> _FakeResponse:
        self.urls.append(url)
        if url.endswith("/queue"):
            return _FakeResponse(200, self.queue)
        return _FakeResponse(self.health_status)


class _FakeProcess:
    def __init__(self, pid: int = 4321, command: list[str] | None = None, cwd: str = r"E:\ExampleEngine") -> None:
        self.pid = pid
        self.info = {"pid": pid, "cmdline": command or managed_command(), "cwd": cwd}
        self.terminated = False

    def cmdline(self) -> list[str]:
        return self.info["cmdline"]

    def cwd(self) -> str:
        return self.info["cwd"]

    def terminate(self) -> None:
        self.terminated = True


class _FakeChild:
    def __init__(self, returncode: int | None = None) -> None:
        self.returncode = returncode
        self.polled = False

    def poll(self) -> int | None:
        self.polled = True
        return self.returncode


class RuntimeStatusTest(unittest.IsolatedAsyncioTestCase):
    async def test_status_is_running_only_when_health_and_managed_process_are_present(self) -> None:
        client = _FakeClient()
        runtime = Runtime(full_config(), tempfile.mkdtemp(), client)
        process = _FakeProcess()

        with patch("backend.runtime.psutil.process_iter", return_value=[process]):
            result = await runtime.status(force=True)

        self.assertEqual(result["state"], "running")
        self.assertTrue(result["online"])
        self.assertEqual(result["pid"], process.pid)

    async def test_status_reports_starting_for_managed_process_without_health(self) -> None:
        client = _FakeClient(health_status=503)
        runtime = Runtime(full_config(), tempfile.mkdtemp(), client)

        with patch("backend.runtime.psutil.process_iter", return_value=[_FakeProcess()]):
            result = await runtime.status(force=True)

        self.assertEqual(result["state"], "starting")
        self.assertFalse(result["online"])

    async def test_status_reports_stopped_when_no_process_and_backend_is_offline(self) -> None:
        client = _FakeClient(health_status=503)
        runtime = Runtime(full_config(), tempfile.mkdtemp(), client)

        with patch("backend.runtime.psutil.process_iter", return_value=[]):
            result = await runtime.status(force=True)

        self.assertEqual(result["state"], "stopped")
        self.assertIsNone(result["pid"])

    async def test_status_reports_child_exit_as_error(self) -> None:
        client = _FakeClient(health_status=503)
        runtime = Runtime(full_config(), tempfile.mkdtemp(), client)
        runtime.child = _FakeChild(returncode=17)

        with patch("backend.runtime.psutil.process_iter", return_value=[]):
            result = await runtime.status(force=True)

        self.assertEqual(result["state"], "error")
        self.assertIn("17", result["error"])


class RuntimeLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runtime = Runtime(full_config(self.temp_dir.name), self.temp_dir.name, _FakeClient())

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_start_launches_when_backend_and_managed_process_are_absent(self) -> None:
        stopped = {"state": "stopped", "online": False, "manageable": True, "error": "", "pid": None}
        starting = {"state": "starting", "online": False, "manageable": True, "error": "", "pid": None}
        self.runtime.status = AsyncMock(side_effect=[stopped, starting])
        self.runtime.processes = Mock(return_value=[])
        self.runtime.launch = Mock()

        result = await self.runtime.action("start")

        self.runtime.launch.assert_called_once_with()
        self.assertEqual(result["state"], "starting")

    async def test_start_is_idempotent_when_backend_is_already_online(self) -> None:
        running = {"state": "running", "online": True, "manageable": True, "error": "", "pid": 4321}
        self.runtime.status = AsyncMock(return_value=running)
        self.runtime.processes = Mock(return_value=[])
        self.runtime.launch = Mock()

        result = await self.runtime.action("start")

        self.assertIs(result, running)
        self.runtime.launch.assert_not_called()

    async def test_stop_rejects_an_online_unmanaged_comfyui(self) -> None:
        running = {"state": "running", "online": True, "manageable": False, "error": "", "pid": None}
        self.runtime.status = AsyncMock(return_value=running)
        self.runtime.processes = Mock(return_value=[])
        self.runtime.idle = AsyncMock()
        self.runtime.terminate = Mock()

        with self.assertRaisesRegex(ValueError, "启动命令不一致"):
            await self.runtime.action("stop")

        self.runtime.idle.assert_not_awaited()
        self.runtime.terminate.assert_not_called()

    async def test_stop_checks_queue_before_terminating_managed_process(self) -> None:
        running = {"state": "running", "online": True, "manageable": True, "error": "", "pid": 4321}
        process = _FakeProcess()
        self.runtime.status = AsyncMock(side_effect=[running, {"state": "stopped", "online": False, "manageable": True, "error": "", "pid": None}])
        self.runtime.processes = Mock(return_value=[process])
        self.runtime.idle = AsyncMock()
        self.runtime.terminate = Mock()

        await self.runtime.action("stop")

        self.runtime.idle.assert_awaited_once_with()
        self.runtime.terminate.assert_called_once_with([process])

    async def test_restart_stops_then_launches_the_managed_process(self) -> None:
        running = {"state": "running", "online": True, "manageable": True, "error": "", "pid": 4321}
        starting = {"state": "starting", "online": False, "manageable": True, "error": "", "pid": None}
        process = _FakeProcess()
        self.runtime.status = AsyncMock(side_effect=[running, starting])
        self.runtime.processes = Mock(return_value=[process])
        self.runtime.idle = AsyncMock()
        self.runtime.terminate = Mock()
        self.runtime.launch = Mock()

        result = await self.runtime.action("restart")

        self.runtime.idle.assert_awaited_once_with()
        self.runtime.terminate.assert_called_once_with([process])
        self.runtime.launch.assert_called_once_with()
        self.assertEqual(result["state"], "starting")

    async def test_unknown_action_is_rejected_without_process_operations(self) -> None:
        self.runtime.status = AsyncMock()
        self.runtime.processes = Mock()

        with self.assertRaisesRegex(ValueError, "不支持"):
            await self.runtime.action("open-shell")

        self.runtime.status.assert_not_awaited()
        self.runtime.processes.assert_not_called()

    async def test_launch_uses_only_configured_executable_args_and_working_directory(self) -> None:
        executable = pathlib.Path(sys.executable)
        config = full_config(self.temp_dir.name)
        config["runtime"]["executable"] = str(executable)
        config["runtime"]["args"] = ["-c", "print('comfy')"]
        runtime = Runtime(config, self.temp_dir.name, _FakeClient())
        child = _FakeChild()

        with patch("backend.runtime.subprocess.Popen", return_value=child) as popen:
            runtime.launch()

        args, kwargs = popen.call_args
        self.assertEqual(args[0], [str(executable), "-c", "print('comfy')"])
        self.assertEqual(kwargs["cwd"], self.temp_dir.name)
        self.assertIs(kwargs["stdin"], __import__("subprocess").DEVNULL)
        self.assertIs(runtime.child, child)


if __name__ == "__main__":
    unittest.main()
