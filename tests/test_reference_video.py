import copy
import unittest

from backend.reference_video import (
    DEFAULT_PRECISION, PRECISION_KEY, PRECISIONS, resize_references, with_reference_precision,
)
from backend.workflows import build_prompt


def recipe():
    return {
        'video': {'class_type': 'VHS_LoadVideo', 'inputs': {
            'video': 'sample.mp4', 'force_rate': 24, 'frame_load_cap': 120, 'skip_first_frames': 24}},
        'condition': {'class_type': 'MiniMaxH3ReferenceToVideo', 'inputs': {
            'width': 608, 'height': 1056, 'length': 124,
            'ref_videos.ref_video_0': ['video', 0],
            'ref_images.ref_image_0': ['image', 0],
            'ref_video_audios.ref_video_audio_0': ['video', 2]}},
        'sampler': {'class_type': 'SelfLiftH3Sampler', 'inputs': {'seed': 123, 'lowres_scale': .6}},
    }


class ReferenceVideo(unittest.TestCase):
    def test_only_goldfish_recipe_gets_one_default_control(self):
        app = dict(graph=recipe(), fields=[dict(key='videos')])
        configured = with_reference_precision(app)
        field = configured['fields'][1]
        self.assertEqual(field['key'], PRECISION_KEY)
        self.assertEqual(field['default'], DEFAULT_PRECISION)
        self.assertEqual(PRECISIONS[field['default']], 512)
        self.assertEqual(with_reference_precision(configured), configured)
        self.assertEqual(len(app['fields']), 1)
        other = dict(graph={'a': {'class_type': 'OtherModel'}}, fields=[])
        self.assertIs(with_reference_precision(other), other)

    def test_reference_only_rewrite_preserves_generation_audio_and_timing(self):
        original = recipe()
        before = copy.deepcopy(original)
        graph = resize_references(original, {PRECISION_KEY: DEFAULT_PRECISION})
        ref = graph['condition']['inputs']['ref_videos.ref_video_0']
        scale = graph.pop(ref[0])
        self.assertEqual(scale['class_type'], 'ImageScaleBy')
        self.assertEqual(scale['inputs']['image'], ['video', 0])
        self.assertEqual(scale['inputs']['upscale_method'], 'area')
        factor = graph.pop(scale['inputs']['scale_by'][0])
        self.assertEqual(factor['class_type'], 'ComfyMathExpression')
        size = graph.pop(factor['inputs']['values.a'][0])
        self.assertEqual(size['inputs']['image'], ['video', 0])
        graph['condition']['inputs']['ref_videos.ref_video_0'] = ['video', 0]
        self.assertEqual(graph, before)
        self.assertEqual(original, before)

    def test_factor_preserves_ratio_never_enlarges_and_handles_orientation(self):
        for label, edge in PRECISIONS.items():
            if edge is None:
                continue
            graph = resize_references(recipe(), {PRECISION_KEY: label})
            expression = next(n['inputs']['expression'] for n in graph.values() if n['class_type'] == 'ComfyMathExpression')
            for width, height in [(1080, 1920), (1920, 1080), (256, 256), (4096, 256)]:
                factor = eval(expression, {'__builtins__': {}, 'min': min, 'max': max}, {'a': width, 'b': height})
                self.assertLessEqual(factor, 1)
                self.assertLessEqual(min(width, height) * factor, edge)
                self.assertLessEqual(max(width, height) * factor, edge * 4)
                self.assertAlmostEqual((width * factor) / (height * factor), width / height)

    def test_original_and_text_only_do_not_insert_resize_nodes(self):
        original = recipe()
        self.assertEqual(resize_references(original, {}), original)
        self.assertEqual(resize_references(original, {PRECISION_KEY: '原始参考 · 较高显存'}), original)
        del original['condition']['inputs']['ref_videos.ref_video_0']
        self.assertEqual(resize_references(original, {PRECISION_KEY: DEFAULT_PRECISION}), original)

    def test_shared_source_reuses_resize_and_existing_node_ids_survive(self):
        original = recipe()
        original['pocket_reference_size'] = {'class_type': 'Existing', 'inputs': {}}
        original['condition']['inputs']['ref_videos.ref_video_1'] = ['video', 0]
        graph = resize_references(original, {PRECISION_KEY: DEFAULT_PRECISION})
        inputs = graph['condition']['inputs']
        self.assertEqual(inputs['ref_videos.ref_video_0'], inputs['ref_videos.ref_video_1'])
        self.assertEqual(graph['pocket_reference_size'], original['pocket_reference_size'])
        self.assertEqual(sum(n['class_type'] == 'ImageScaleBy' for n in graph.values()), 1)

    def test_native_app_build_accepts_control_without_a_canvas_widget(self):
        app = with_reference_precision(dict(graph=recipe(), fields=[], imageGroups=[]))
        graph, values = build_prompt(app, {}, {})
        self.assertEqual(values[PRECISION_KEY], DEFAULT_PRECISION)
        self.assertNotEqual(resize_references(graph, values), graph)
        with self.assertRaises(ValueError):
            build_prompt(app, {PRECISION_KEY: 'invalid'}, {})


if __name__ == '__main__':
    unittest.main()
