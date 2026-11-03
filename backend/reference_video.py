"""Bound H3 reference conditioning without changing the generated video size."""
import copy


PRECISION_KEY = 'pocket_reference_precision'
PRECISIONS = {
    '省显存 · 短边上限 320': 320,
    '均衡 · 短边上限 384（推荐）': 384,
    '精细 · 短边上限 512': 512,
    '原始参考 · 较高显存': None,
}
DEFAULT_PRECISION = '均衡 · 短边上限 384（推荐）'


def with_reference_precision(app):
    """Expose one Pocket-only control on the existing Goldfish/SelfLift recipe."""
    types = {node['class_type'] for node in app['graph'].values()}
    if not {'MiniMaxH3ReferenceToVideo', 'SelfLiftH3Sampler'} <= types:
        return app
    app = copy.deepcopy(app)
    if not any(field['key'] == PRECISION_KEY for field in app['fields']):
        field = dict(key=PRECISION_KEY, label='参考视频精度（不改变成片分辨率）',
                     kind='select', default=DEFAULT_PRECISION, options=list(PRECISIONS),
                     pocket_control=True,
                     help='只缩小模型看的参考画面，保持比例、时长和声音。均衡档先试 3～5 秒；表情或手指细节不足再选精细。')
        index = next((i + 1 for i, f in enumerate(app['fields']) if f['key'] == 'videos'), len(app['fields']))
        app['fields'].insert(index, field)
    return app


def resize_references(graph, values):
    """Insert CPU image-batch scaling only on video ports into H3 conditioning.

    Runtime dimensions also cover old uploads with no width/height metadata.
    No crop, no frame sampling, no audio edits and no enlargement of small clips.
    Comfy's H3 node performs its own final spatial grid alignment afterwards.
    """
    if PRECISION_KEY not in values:
        return graph
    precision = values[PRECISION_KEY]
    if not isinstance(precision, str) or precision not in PRECISIONS:
        raise ValueError('参考视频精度无效')
    short_edge = PRECISIONS[precision]
    if short_edge is None:
        return graph
    graph = copy.deepcopy(graph)
    resized = {}

    def add(suffix, typ, inputs):
        key = 'pocket_reference_' + suffix
        while key in graph:
            key += '_'
        graph[key] = dict(class_type=typ, inputs=inputs)
        return [key, 0]

    for node in list(graph.values()):
        if node['class_type'] != 'MiniMaxH3ReferenceToVideo':
            continue
        for port, source in list(node['inputs'].items()):
            if not port.startswith('ref_videos.') or not isinstance(source, list) or len(source) != 2:
                continue
            ref = tuple(source)
            if ref not in resized:
                size = add('size', 'GetImageSize', {'image': source})
                # Bound pathological aspect ratios too. Normal 9:16/16:9 clips
                # are constrained by their short edge, not by this long edge.
                factor = add('factor', 'ComfyMathExpression', {
                    'expression': f'min(1, {short_edge} / min(a, b), {short_edge * 4} / max(a, b))',
                    'values.a': [size[0], 0], 'values.b': [size[0], 1]})
                resized[ref] = add('scale', 'ImageScaleBy', {
                    'image': source, 'upscale_method': 'area', 'scale_by': factor})
            node['inputs'][port] = resized[ref]
    return graph
