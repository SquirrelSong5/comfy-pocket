"""Behavioral tests for the on-disk application preferences store."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.preferences import Preferences


class PreferencesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "preferences.json"
        self.image_app = {
            "id": "image",
            "fields": [
                {"key": "prompt", "kind": "text", "default": "default prompt"},
                {"key": "steps", "kind": "int", "min": 0, "max": 100, "default": 12},
                {
                    "key": "strength",
                    "kind": "float",
                    "min": 0.0,
                    "max": 1.0,
                    "default": 0.75,
                },
                {"key": "enabled", "kind": "bool", "default": True},
                {
                    "key": "mode",
                    "kind": "select",
                    "options": ["fast", "quality"],
                    "default": "fast",
                },
                {"key": "reference", "kind": "image", "default": None},
            ],
        }
        self.edit_app = {
            "id": "edit",
            "fields": [
                {"key": "prompt", "kind": "text", "default": "edit prompt"},
                {"key": "steps", "kind": "int", "min": 0, "max": 100, "default": 20},
                {"key": "enabled", "kind": "bool", "default": False},
            ],
        }
        self.catalog = {app["id"]: app for app in (self.image_app, self.edit_app)}

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_new_instance_restores_saved_values_from_disk(self) -> None:
        preferences = Preferences(self.path)
        preferences.update(
            self.image_app,
            {
                "prompt": "saved prompt",
                "steps": 0,
                "strength": 0.0,
                "enabled": False,
                "mode": "quality",
            },
        )

        restored = Preferences(self.path)

        self.assertEqual(
            restored.snapshot(self.catalog),
            {
                "selected": "image",
                "drafts": {
                    "image": {
                        "prompt": "saved prompt",
                        "steps": 0,
                        "strength": 0.0,
                        "enabled": False,
                        "mode": "quality",
                    },
                    "edit": {
                        "prompt": "edit prompt",
                        "steps": 20,
                        "enabled": False,
                    },
                },
            },
        )

    def test_updates_are_isolated_per_application_and_partial_patches_merge(self) -> None:
        preferences = Preferences(self.path)
        preferences.update(self.image_app, {"prompt": "image prompt", "steps": 18})
        preferences.update(self.image_app, {"enabled": False})
        preferences.update(self.edit_app, {"prompt": "edit prompt", "steps": 7})

        snapshot = preferences.snapshot(self.catalog)

        self.assertEqual(snapshot["drafts"]["image"]["prompt"], "image prompt")
        self.assertEqual(snapshot["drafts"]["image"]["steps"], 18)
        self.assertFalse(snapshot["drafts"]["image"]["enabled"])
        self.assertEqual(snapshot["drafts"]["edit"]["prompt"], "edit prompt")
        self.assertEqual(snapshot["drafts"]["edit"]["steps"], 7)
        self.assertFalse(snapshot["drafts"]["edit"]["enabled"])

    def test_zero_false_and_empty_text_are_persisted(self) -> None:
        preferences = Preferences(self.path)

        preferences.update(
            self.image_app,
            {"prompt": "", "steps": 0, "strength": 0.0, "enabled": False},
        )

        self.assertEqual(
            preferences.snapshot(self.catalog)["drafts"]["image"],
            {"prompt": "", "steps": 0, "strength": 0.0, "enabled": False, "mode": "fast"},
        )

    def test_invalid_values_unknown_fields_and_images_leave_memory_and_file_unchanged(self) -> None:
        preferences = Preferences(self.path)
        preferences.update(self.image_app, {"prompt": "keep", "steps": 8, "strength": 0.5})
        before_snapshot = preferences.snapshot(self.catalog)
        before_file = self.path.read_bytes()

        invalid_updates = (
            {"strength": float("nan")},
            {"strength": float("inf")},
            {"strength": float("-inf")},
            {"steps": True},
            {"strength": False},
            {"unknown": "value"},
            {"reference": "image.png"},
        )
        for values in invalid_updates:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    preferences.update(self.image_app, values)
                self.assertEqual(preferences.snapshot(self.catalog), before_snapshot)
                self.assertEqual(self.path.read_bytes(), before_file)

    def test_changed_workflow_fields_and_removed_select_options_fall_back_to_defaults(self) -> None:
        preferences = Preferences(self.path)
        preferences.update(self.image_app, {"steps": 80, "mode": "quality"})

        changed_app = {
            "id": "image",
            "fields": [
                {"key": "steps", "kind": "int", "min": 0, "max": 20, "default": 6},
                {
                    "key": "mode",
                    "kind": "select",
                    "options": ["fast"],
                    "default": "fast",
                },
            ],
        }

        self.assertEqual(
            preferences.snapshot({"image": changed_app}),
            {"selected": "image", "drafts": {"image": {"steps": 6, "mode": "fast"}}},
        )

    def test_reset_only_clears_the_target_application(self) -> None:
        preferences = Preferences(self.path)
        preferences.update(self.image_app, {"prompt": "image saved", "steps": 4})
        preferences.update(self.edit_app, {"prompt": "edit saved", "steps": 9})

        preferences.update(self.image_app, reset=True)

        snapshot = preferences.snapshot(self.catalog)
        self.assertEqual(snapshot["selected"], "image")
        self.assertEqual(
            snapshot["drafts"]["image"],
            {
                "prompt": "default prompt",
                "steps": 12,
                "strength": 0.75,
                "enabled": True,
                "mode": "fast",
            },
        )
        self.assertEqual(snapshot["drafts"]["edit"]["prompt"], "edit saved")
        self.assertEqual(snapshot["drafts"]["edit"]["steps"], 9)

    def test_failed_write_keeps_memory_and_existing_file(self) -> None:
        preferences = Preferences(self.path)
        preferences.update(self.image_app, {"prompt": "before", "steps": 5})
        before_snapshot = preferences.snapshot(self.catalog)
        before_file = self.path.read_bytes()

        with patch.object(Path, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                preferences.update(self.image_app, {"prompt": "after"})

        self.assertEqual(preferences.snapshot(self.catalog), before_snapshot)
        self.assertEqual(self.path.read_bytes(), before_file)

    def test_empty_catalog_returns_persisted_data_for_offline_reading(self) -> None:
        preferences = Preferences(self.path)
        preferences.update(self.image_app, {"prompt": "offline", "steps": 3})

        offline = Preferences(self.path).snapshot({})

        self.assertEqual(
            offline,
            {
                "selected": "image",
                "drafts": {"image": {"prompt": "offline", "steps": 3}},
            },
        )
        offline["drafts"]["image"]["prompt"] = "mutated copy"
        self.assertEqual(
            Preferences(self.path).snapshot({})["drafts"]["image"]["prompt"],
            "offline",
        )


if __name__ == "__main__":
    unittest.main()
