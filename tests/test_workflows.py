"""Contract tests for the dynamic ComfyUI application adapter.

The small in-memory application below deliberately uses node names that are not
part of the built-in app catalogue.  Its schemas are supplied through
``object_info`` so the tests exercise the same data-driven path as a newly
installed official app.
"""

from __future__ import annotations

import copy
import json
import math
import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.workflows import build_prompt, compile_app, public_app


def _dynamic_object_info() -> dict:
    """Return schemas for a deliberately new, catalogue-independent app."""

    return {
        "PromptNode": {
            "input": {
                "required": {
                    "prompt": ["STRING", {"default": "initial prompt", "multiline": True}],
                }
            }
        },
        "CountNode": {
            "input": {
                "required": {
                    "value": ["INT", {"default": 0, "min": 0, "max": 8}],
                }
            }
        },
        "ToggleNode": {
            "input": {
                "required": {
                    "value": ["BOOLEAN", {"default": False}],
                }
            }
        },
        "StrengthNode": {
            "input": {
                "required": {
                    "value": ["FLOAT", {"default": 0.5, "min": 0, "max": 1}],
                }
            }
        },
        "ModeNode": {
            "input": {
                "required": {
                    "value": [["fast", "quality"], {}],
                }
            }
        },
        "IntNode": {
            "input": {
                "required": {
                    "value": ["INT", {"default": 2, "min": 0, "max": 8}],
                }
            }
        },
        "BoolNode": {
            "input": {
                "required": {
                    "value": ["BOOLEAN", {"default": False}],
                }
            }
        },
        "LoadImage": {
            "input": {
                "required": {
                    "image": ["STRING", {"default": "fixture.png"}],
                }
            }
        },
        "DynamicOutput": {
            "input": {
                "required": {
                    "prompt": ["STRING", {}],
                    "count": ["INT", {}],
                    "toggle": ["BOOLEAN", {}],
                    "strength": ["FLOAT", {}],
                    "mode": ["STRING", {}],
                    "int_param": ["INT", {}],
                    "bool_param": ["BOOLEAN", {}],
                    **{
                        f"image{i}": ["IMAGE", {}]
                        for i in range(1, 9)
                    },
                }
            }
        },
    }


def _dynamic_workflow() -> dict:
    """Build an eight-slot optional-image app with count and toggle controls."""

    nodes = [
        {
            "id": "prompt",
            "type": "PromptNode",
            "title": "Prompt",
            "widgets_values": ["initial prompt"],
            "inputs": [],
        },
        {
            "id": "count",
            "type": "CountNode",
            "title": "Image count",
            "widgets_values": [0],
            "inputs": [],
        },
        {
            "id": "toggle",
            "type": "ToggleNode",
            "title": "Use multiple images",
            "widgets_values": [False],
            "inputs": [],
        },
        {
            "id": "strength",
            "type": "StrengthNode",
            "title": "Strength",
            "widgets_values": [0.5],
            "inputs": [],
        },
        {
            "id": "mode",
            "type": "ModeNode",
            "title": "Mode",
            "widgets_values": ["fast"],
            "inputs": [],
        },
        {
            "id": "int_param",
            "type": "IntNode",
            "title": "Independent integer",
            "widgets_values": [2],
            "inputs": [],
        },
        {
            "id": "bool_param",
            "type": "BoolNode",
            "title": "Independent boolean",
            "widgets_values": [False],
            "inputs": [],
        },
    ]
    image_ids = [f"image{i}" for i in range(1, 9)]
    for index, ident in enumerate(image_ids, start=1):
        nodes.append(
            {
                "id": ident,
                "type": "LoadImage",
                "title": f"Image {index}",
                "widgets_values": [f"placeholder-{index}.png"],
                "inputs": [],
            }
        )

    links = []

    def output_input(name: str, origin: str) -> dict:
        link_id = len(links) + 1
        links.append([link_id, origin, 0, "output", name, "*"])
        return {"name": name, "type": "*", "link": link_id}

    output_inputs = [
        output_input("prompt", "prompt"),
        output_input("count", "count"),
        output_input("toggle", "toggle"),
        output_input("strength", "strength"),
        output_input("mode", "mode"),
        output_input("int_param", "int_param"),
        output_input("bool_param", "bool_param"),
    ]
    output_inputs.extend(output_input(f"image{i}", f"image{i}") for i in range(1, 9))
    nodes.append(
        {
            "id": "output",
            "type": "DynamicOutput",
            "title": "Dynamic output",
            "widgets_values": [],
            "inputs": output_inputs,
        }
    )

    uuid = "dynamic-app-uuid"
    inputs = [
        [f"{uuid}:prompt:prompt", "Prompt"],
        [f"{uuid}:count:value", "Image count"],
        [f"{uuid}:toggle:value", "Use multiple images"],
        [f"{uuid}:strength:value", "Strength"],
        [f"{uuid}:mode:value", "Mode"],
        [f"{uuid}:int_param:value", "Independent integer"],
        [f"{uuid}:bool_param:value", "Independent boolean"],
    ]
    inputs.extend(
        [f"{uuid}:image{i}:image", f"Image {i}"]
        for i in range(1, 9)
    )
    return {
        "nodes": nodes,
        "links": links,
        "extra": {
            "linearData": {"inputs": inputs, "outputs": ["output"]},
            "comfyLite": {
                "description": "Dynamic test app",
                "imageGroups": [
                    {
                        "label": "Reference images",
                        "fields": [f"image{i}.image" for i in range(1, 9)],
                        "min": 0,
                        "count": "count.value",
                        "toggle": "toggle.value",
                    }
                ],
            },
        },
    }


def _nested_dynamic_object_info() -> dict:
    return {
        "NestedNode": {
            "input": {
                "required": {
                    "mode": [
                        "COMFY_DYNAMICCOMBO_V3",
                        {
                            "options": [
                                {
                                    "key": "basic",
                                    "inputs": {
                                        "required": {
                                            "preset": [["one", "two"], {}],
                                        }
                                    },
                                },
                                {
                                    "key": "advanced",
                                    "inputs": {
                                        "required": {
                                            "detail": [
                                                "COMFY_DYNAMICCOMBO_V3",
                                                {
                                                    "options": [
                                                        {
                                                            "key": "deep",
                                                            "inputs": {
                                                                "required": {
                                                                    "strength": [
                                                                        "INT",
                                                                        {"default": 4, "min": 0, "max": 10},
                                                                    ]
                                                                }
                                                            },
                                                        }
                                                    ]
                                                },
                                            ]
                                        }
                                    },
                                },
                            ]
                        },
                    ],
                }
            }
        }
    }


def _nested_dynamic_workflow() -> dict:
    uuid = "nested-dynamic-uuid"
    return {
        "nodes": [
            {
                "id": "nested",
                "type": "NestedNode",
                "title": "Nested dynamic node",
                "widgets_values": ["advanced", "deep", 7],
                "inputs": [],
            }
        ],
        "links": [],
        "extra": {
            "linearData": {
                "inputs": [
                    [f"{uuid}:nested:mode", "Mode"],
                    [f"{uuid}:nested:mode.detail", "Detail"],
                    [f"{uuid}:nested:mode.detail.strength", "Strength"],
                ],
                "outputs": ["nested"],
            }
        },
    }


def _bypass_object_info() -> dict:
    return {
        "SourceNode": {
            "input": {
                "required": {
                    "value": ["STRING", {"default": "source"}],
                }
            }
        },
        "BypassNode": {
            "input": {
                "required": {
                    "input": ["STRING", {}],
                }
            }
        },
        "OutputNode": {
            "input": {
                "required": {
                    "value": ["STRING", {}],
                }
            }
        },
    }


def _bypass_workflow() -> dict:
    return {
        "nodes": [
            {
                "id": "src",
                "type": "SourceNode",
                "title": "Source",
                "widgets_values": ["source"],
                "inputs": [],
            },
            {
                "id": "bypass",
                "type": "BypassNode",
                "title": "Bypass",
                "mode": 4,
                "widgets_values": [],
                "inputs": [{"name": "input", "type": "STRING", "link": 1}],
                "outputs": [{"type": "STRING"}],
            },
            {
                "id": "out",
                "type": "OutputNode",
                "title": "Output",
                "widgets_values": [],
                "inputs": [{"name": "value", "type": "STRING", "link": 2}],
            },
        ],
        "links": [
            [1, "src", 0, "bypass", 0, "STRING"],
            [2, "bypass", 0, "out", 0, "STRING"],
        ],
        "extra": {
            "linearData": {
                "inputs": [["bypass-uuid:src:value", "Value"]],
                "outputs": ["out"],
            }
        },
    }


class WorkflowAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = _dynamic_workflow()
        self.object_info = _dynamic_object_info()
        self.app = compile_app("/new-vendor/New model · Dynamic.app.json", self.workflow, self.object_info)

    def _values(self) -> dict:
        return {
            "prompt.prompt": "updated prompt",
            "count.value": 99,
            "toggle.value": False,
            "strength.value": 0.75,
            "mode.value": "quality",
            "int_param.value": 2,
            "bool_param.value": False,
        }

    def test_new_schema_driven_app_compiles_without_catalogue_branch(self) -> None:
        self.assertEqual(self.app["name"], "Dynamic")
        self.assertEqual(self.app["model"], "New model")
        self.assertIn("DynamicOutput", {node["class_type"] for node in self.app["graph"].values()})
        self.assertEqual(len(self.app["imageGroups"][0]["fields"]), 8)
        self.assertEqual({field["kind"] for field in self.app["fields"]}, {"text", "int", "bool", "float", "select", "image"})

    def test_public_app_hides_graph_path_and_internal_field_refs(self) -> None:
        public = public_app(self.app)
        self.assertNotIn("graph", public)
        self.assertNotIn("path", public)
        for field in public["fields"]:
            self.assertNotIn("node", field)
            self.assertNotIn("widget", field)

    def test_optional_image_group_supports_zero_one_two_and_eight(self) -> None:
        image_keys = [f"image{i}.image" for i in range(1, 9)]
        for count in (0, 1, 2, 8):
            with self.subTest(count=count):
                values = self._values()
                images = {key: f"upload-{index}.png" for index, key in enumerate(image_keys[:count], start=1)}
                prompt, normalized = build_prompt(self.app, values, images)

                self.assertEqual(normalized["count.value"], count)
                self.assertEqual(normalized["toggle.value"], count > 1)
                self.assertEqual(prompt["count"]["inputs"]["value"], count)
                self.assertEqual(prompt["toggle"]["inputs"]["value"], count > 1)
                for index, key in enumerate(image_keys, start=1):
                    expected = f"upload-{index}.png" if index <= count else ""
                    self.assertEqual(normalized[key], expected)
                    self.assertEqual(prompt[f"image{index}"]["inputs"]["image"], expected)

    def test_build_prompt_does_not_mutate_compiled_template_or_input_values(self) -> None:
        original_workflow = copy.deepcopy(self.workflow)
        original_values = self._values()
        original_app_graph = copy.deepcopy(self.app["graph"])
        values = copy.deepcopy(original_values)
        build_prompt(self.app, values, {"image1.image": "upload.png"})

        self.assertEqual(self.workflow, original_workflow)
        self.assertEqual(values, original_values)
        self.assertEqual(self.app["graph"], original_app_graph)

    def test_unknown_parameter_is_rejected_in_values_or_images(self) -> None:
        with self.assertRaisesRegex(ValueError, "未公开"):
            build_prompt(self.app, {**self._values(), "does.not.exist": "x"}, {})
        with self.assertRaisesRegex(ValueError, "未公开"):
            build_prompt(self.app, self._values(), {"does.not.exist": "upload.png"})

    def test_image_fields_cannot_be_satisfied_by_values_paths(self) -> None:
        values = {**self._values(), "image1.image": r"C:\outside\arbitrary.png"}
        prompt, normalized = build_prompt(self.app, values, {})
        self.assertEqual(normalized["image1.image"], "")
        self.assertEqual(prompt["image1"]["inputs"]["image"], "")

        strict_workflow = copy.deepcopy(self.workflow)
        strict_workflow["extra"]["comfyLite"]["imageGroups"] = []
        for node in strict_workflow["nodes"]:
            if node["type"] == "LoadImage":
                node["widgets_values"] = [""]
        strict_app = compile_app("/new-vendor/required-image.app.json", strict_workflow, self.object_info)
        strict_values = {**values, "count.value": 0}
        with self.assertRaisesRegex(ValueError, "请上传"):
            build_prompt(strict_app, strict_values, {})

    def test_parameter_types_and_ranges_are_validated(self) -> None:
        invalid_cases = (
            ({**self._values(), "prompt.prompt": 123}, {}, "文本"),
            ({**self._values(), "prompt.prompt": "x" * 12001}, {}, "文本"),
            ({**self._values(), "int_param.value": True}, {}, "有效数字"),
            ({**self._values(), "int_param.value": 9}, {}, "超出范围"),
            ({**self._values(), "int_param.value": 1.5}, {}, "整数"),
            ({**self._values(), "strength.value": math.nan}, {}, "有效数字"),
            ({**self._values(), "strength.value": 1.1}, {}, "超出范围"),
            ({**self._values(), "bool_param.value": 1}, {}, "开关值"),
            ({**self._values(), "mode.value": "unknown"}, {}, "选项无效"),
            (self._values(), {"prompt.prompt": "not-an-image"}, "图片输入无效"),
        )
        for values, images, message in invalid_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_prompt(self.app, values, images)

    def test_unsupported_node_on_selected_output_path_is_rejected(self) -> None:
        workflow = _dynamic_workflow()
        workflow["nodes"].append(
            {
                "id": "unsupported",
                "type": "NodeFromAnUninstalledExtension",
                "title": "Unsupported",
                "widgets_values": [],
                "inputs": [],
            }
        )
        workflow["extra"]["linearData"] = {"inputs": [], "outputs": ["unsupported"]}

        with self.assertRaisesRegex(ValueError, "支持|缺失"):
            compile_app("/new-vendor/unsupported.app.json", workflow, self.object_info)

    def test_nested_dynamic_combo_is_parsed_and_exposed_recursively(self) -> None:
        workflow = _nested_dynamic_workflow()
        app = compile_app(
            "/new-vendor/nested-dynamic.app.json",
            workflow,
            _nested_dynamic_object_info(),
        )
        fields = {field["key"]: field for field in app["fields"]}
        self.assertEqual(
            set(fields),
            {"nested.mode", "nested.mode.detail", "nested.mode.detail.strength"},
        )
        self.assertEqual(fields["nested.mode"]["options"], ["basic", "advanced"])
        self.assertEqual(fields["nested.mode.detail"]["options"], ["deep"])
        self.assertEqual(fields["nested.mode.detail.strength"]["kind"], "int")

        prompt, normalized = build_prompt(
            app,
            {
                "nested.mode": "advanced",
                "nested.mode.detail": "deep",
                "nested.mode.detail.strength": 9,
            },
            {},
        )
        self.assertEqual(normalized["nested.mode.detail.strength"], 9)
        self.assertEqual(prompt["nested"]["inputs"]["mode.detail.strength"], 9)

        invalid = copy.deepcopy(workflow)
        invalid["nodes"][0]["widgets_values"] = ["unknown", "deep", 7]
        with self.assertRaisesRegex(ValueError, "动态选项"):
            compile_app("/new-vendor/nested-dynamic-invalid.app.json", invalid, _nested_dynamic_object_info())

    def test_mode_four_bypass_is_resolved_to_its_source(self) -> None:
        app = compile_app("/new-vendor/mode-four.app.json", _bypass_workflow(), _bypass_object_info())
        self.assertNotIn("bypass", app["graph"])
        self.assertEqual(app["graph"]["out"]["inputs"]["value"], ["src", 0])
        self.assertEqual(app["fields"][0]["key"], "src.value")


if __name__ == "__main__":
    unittest.main()
