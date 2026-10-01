"""Tests for translating ComfyUI websocket execution events into job state.

The progress reducer is deliberately tested with a small in-memory job map.
This keeps the contract independent from the HTTP server and makes sure an
event for one prompt cannot leak into another prompt's state.
"""

from __future__ import annotations

import copy
import math
import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.progress import apply_event


def _jobs() -> dict:
    return {
        "prompt-queued": {
            "status": "queued",
            "phase": "queued",
            "node_labels": {"12": "采样器"},
        },
        "prompt-running": {
            "status": "running",
            "phase": "running",
            "node_labels": {"12": "采样器"},
            "progress": {"node": "12", "label": "采样器", "value": 3, "max": 10},
        },
        "prompt-done": {
            "status": "success",
            "phase": "succeeded",
            "node_labels": {"12": "采样器"},
            "progress": {"node": "12", "label": "采样器", "value": 10, "max": 10},
        },
    }


def _event(event_type: str, prompt_id: str, **data: object) -> dict:
    return {"type": event_type, "data": {"prompt_id": prompt_id, **data}}


class ProgressEventTest(unittest.TestCase):
    def test_execution_start_moves_known_queued_job_to_running(self) -> None:
        jobs = _jobs()

        changed = apply_event(jobs, _event("execution_start", "prompt-queued"))

        self.assertTrue(changed)
        self.assertEqual(jobs["prompt-queued"]["status"], "running")

    def test_executing_switches_node_and_uses_label_fallback(self) -> None:
        jobs = _jobs()

        apply_event(jobs, _event("executing", "prompt-running", node="12"))
        self.assertEqual(
            jobs["prompt-running"]["progress"],
            {"node": "12", "label": "采样器", "value": 0, "max": 0},
        )

        apply_event(jobs, _event("executing", "prompt-running", node="unknown"))
        self.assertEqual(
            jobs["prompt-running"]["progress"],
            {"node": "unknown", "label": "unknown", "value": 0, "max": 0},
        )

    def test_progress_updates_node_and_clamps_value(self) -> None:
        jobs = _jobs()

        apply_event(
            jobs,
            _event("progress", "prompt-running", node="12", value=14, max=10),
        )
        self.assertEqual(
            jobs["prompt-running"]["progress"],
            {"node": "12", "label": "采样器", "value": 10, "max": 10},
        )

        apply_event(
            jobs,
            _event("progress", "prompt-running", node="12", value=-2, max=10),
        )
        self.assertEqual(jobs["prompt-running"]["progress"]["value"], 0)

    def test_invalid_progress_numbers_are_ignored_without_corrupting_state(self) -> None:
        jobs = _jobs()
        original = copy.deepcopy(jobs["prompt-running"])

        for value, maximum in (
            (math.nan, 10),
            (math.inf, 10),
            (2, 0),
            (2, -1),
            ("bad", 10),
        ):
            with self.subTest(value=value, maximum=maximum):
                self.assertFalse(
                    apply_event(
                        jobs,
                        _event(
                            "progress",
                            "prompt-running",
                            node="12",
                            value=value,
                            max=maximum,
                        ),
                    )
                )
                self.assertEqual(jobs["prompt-running"], original)

    def test_unknown_prompt_and_other_prompt_are_isolated(self) -> None:
        jobs = _jobs()
        before = copy.deepcopy(jobs)

        self.assertFalse(apply_event(jobs, _event("progress", "missing", node="12", value=1, max=2)))
        self.assertEqual(jobs, before)

        apply_event(jobs, _event("progress", "prompt-running", node="12", value=1, max=2))
        self.assertEqual(jobs["prompt-queued"], before["prompt-queued"])
        self.assertEqual(jobs["prompt-done"], before["prompt-done"])

    def test_terminal_job_is_not_modified_by_late_execution_events(self) -> None:
        jobs = _jobs()
        before = copy.deepcopy(jobs["prompt-done"])

        self.assertFalse(apply_event(jobs, _event("execution_start", "prompt-done")))
        self.assertFalse(apply_event(jobs, _event("executing", "prompt-done", node="12")))
        self.assertFalse(apply_event(jobs, _event("progress", "prompt-done", node="12", value=1, max=10)))
        self.assertEqual(jobs["prompt-done"], before)

    def test_executing_without_node_enters_finishing_and_waits_for_history(self) -> None:
        jobs = _jobs()
        before = copy.deepcopy(jobs["prompt-running"])

        changed = apply_event(jobs, _event("executing", "prompt-running", node=None))

        self.assertTrue(changed)
        self.assertEqual(jobs["prompt-running"]["phase"], "finishing")
        self.assertNotIn("progress", jobs["prompt-running"])
        self.assertNotEqual(jobs["prompt-running"], before)

    def test_error_and_interrupted_enter_finishing_without_claiming_success(self) -> None:
        for event_type in ("execution_error", "execution_interrupted"):
            with self.subTest(event_type=event_type):
                jobs = _jobs()
                apply_event(jobs, _event(event_type, "prompt-running"))
                self.assertEqual(jobs["prompt-running"]["phase"], "finishing")
                self.assertNotEqual(jobs["prompt-running"]["phase"], "succeeded")

    def test_executed_accepts_text_array_and_string(self) -> None:
        for output, expected in (
            ({"text": ["第一行", "第二行"]}, "第一行\n第二行"),
            ({"text": "单段文本"}, "单段文本"),
        ):
            with self.subTest(output=output):
                jobs = _jobs()
                changed = apply_event(
                    jobs,
                    _event("executed", "prompt-running", node="12", output=output),
                )

                self.assertTrue(changed)
                self.assertEqual(
                    jobs["prompt-running"]["texts"],
                    [{"node": "12", "label": "采样器", "text": expected}],
                )

    def test_executed_replaces_same_node_without_duplicates(self) -> None:
        jobs = _jobs()

        apply_event(
            jobs,
            _event("executed", "prompt-running", node="12", output={"text": "旧文本"}),
        )
        apply_event(
            jobs,
            _event("executed", "prompt-running", node="12", output={"text": "新文本"}),
        )
        apply_event(
            jobs,
            _event("executed", "prompt-running", node="13", output={"text": "另一个节点"}),
        )

        self.assertEqual(
            jobs["prompt-running"]["texts"],
            [
                {"node": "12", "label": "采样器", "text": "新文本"},
                {"node": "13", "label": "文本输出", "text": "另一个节点"},
            ],
        )

    def test_executed_does_not_leak_to_other_or_unknown_jobs(self) -> None:
        jobs = _jobs()
        before = copy.deepcopy(jobs)

        self.assertFalse(
            apply_event(
                jobs,
                _event("executed", "missing", node="12", output={"text": "未知任务"}),
            )
        )
        self.assertFalse(
            apply_event(
                jobs,
                _event("executed", "prompt-running", node="12", output={"text": ""}),
            )
        )
        self.assertNotIn("texts", jobs["prompt-running"])
        self.assertEqual(jobs["prompt-queued"], before["prompt-queued"])
        self.assertEqual(jobs["prompt-done"], before["prompt-done"])

    def test_executed_ignores_non_text_output_and_truncates_long_text(self) -> None:
        jobs = _jobs()

        for output in ({"text": [1, None, False]}, {"text": 123}, {"text": []}):
            with self.subTest(output=output):
                self.assertFalse(
                    apply_event(
                        jobs,
                        _event("executed", "prompt-running", node="12", output=output),
                    )
                )
                self.assertNotIn("texts", jobs["prompt-running"])

        long_text = "x" * 30005
        self.assertTrue(
            apply_event(
                jobs,
                _event(
                    "executed",
                    "prompt-running",
                    node="12",
                    output={"text": long_text},
                ),
            )
        )
        self.assertEqual(len(jobs["prompt-running"]["texts"][0]["text"]), 30000)

    def test_execution_success_waits_for_history_instead_of_marking_success(self) -> None:
        jobs = _jobs()

        changed = apply_event(jobs, _event("execution_success", "prompt-running"))

        self.assertTrue(changed)
        self.assertEqual(jobs["prompt-running"]["status"], "running")
        self.assertEqual(jobs["prompt-running"]["phase"], "finishing")
        self.assertNotIn("progress", jobs["prompt-running"])


if __name__ == "__main__":
    unittest.main()
