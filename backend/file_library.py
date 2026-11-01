"""Authenticated, read-only browsing of local ComfyUI input/output folders."""
import asyncio
import hashlib
import pathlib
import shutil
import subprocess

from aiohttp import web

from .previews import make_preview

KINDS = {
    'image': {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.avif'},
    'video': {'.mp4', '.webm', '.mkv', '.mov', '.avi'},
    'audio': {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.opus'},
}


def file_kind(path):
    return next((kind for kind, suffixes in KINDS.items() if path.suffix.lower() in suffixes), 'file')


def linked(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def video_preview(path):
    """Decode one small CPU frame; never load the full video into memory."""
    executable = shutil.which('ffmpeg')
    if not executable:
        try:
            import imageio_ffmpeg
            executable = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            raise ValueError('电脑未找到 ffmpeg，暂时无法生成视频缩略图')
    for seek in ('0.2', '0'):
        try:
            result = subprocess.run([executable, '-nostdin', '-hide_banner', '-loglevel', 'error',
                '-ss', seek, '-i', str(path), '-map', '0:v:0', '-frames:v', '1', '-an',
                '-vf', 'scale=480:480:force_original_aspect_ratio=decrease',
                '-threads', '1', '-f', 'image2pipe', '-vcodec', 'mjpeg', 'pipe:1'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired as error:
            raise ValueError('视频缩略图读取超时，可以直接打开视频') from error
        if result.returncode == 0 and result.stdout:
            return make_preview(result.stdout)
    raise ValueError('无法读取视频缩略图，可以直接打开或下载视频')


class FileLibrary:
    def __init__(self, root):
        self.root = pathlib.Path(root).resolve()

    def resolve(self, value):
        if not isinstance(value, str) or '\\' in value or ':' in value or '\0' in value:
            raise ValueError('文件路径无效')
        relative = pathlib.PurePosixPath(value)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('只能浏览所选文件夹内的内容')
        candidate = self.root
        for part in relative.parts:
            candidate = candidate / part
            if linked(candidate):
                raise ValueError('不支持访问链接目录或文件')
        target = candidate.resolve()
        if not target.is_relative_to(self.root):
            raise ValueError('只能浏览所选文件夹内的内容')
        return target

    def listing(self, path='', kind='all', search='', offset=0, limit=60):
        if kind not in ('all', *KINDS, 'file') or offset < 0 or not 1 <= limit <= 100 or len(search) > 200:
            raise ValueError('筛选参数无效')
        folder = self.resolve(path)
        if not folder.is_dir():
            raise FileNotFoundError('文件夹不存在')
        entries = []
        pending = [folder]
        while pending:
            try:
                children = list(pending.pop().iterdir())
            except (FileNotFoundError, PermissionError):
                continue
            for item in children:
                try:
                    if item.name.startswith('.') or linked(item):
                        continue
                    if item.is_dir():
                        pending.append(item)
                        continue
                    if not item.is_file():
                        continue
                    category = file_kind(item)
                    relative = item.relative_to(self.root).as_posix()
                    if search.casefold() not in relative.casefold() or (kind != 'all' and category != kind):
                        continue
                    stat = item.stat()
                    entries.append(dict(name=item.name, path=relative,
                                        kind=category, size=stat.st_size, modified=stat.st_mtime))
                except (FileNotFoundError, PermissionError):
                    continue
        entries.sort(key=lambda item: (-item['modified'], item['path']))
        return dict(path='' if folder == self.root else folder.relative_to(self.root).as_posix(),
                    entries=entries[offset:offset + limit], total=len(entries),
                    next_offset=offset + limit if offset + limit < len(entries) else None)


def install(app, server):
    libraries = {kind: FileLibrary(root) for kind in ('input', 'output')
                 if (root := server.CONF.get(kind + '_directory'))}

    def configured(request):
        kind = request.query.get('root', 'output')
        if kind not in ('input', 'output'):
            raise ValueError('文件夹类型无效')
        if kind not in libraries:
            raise ValueError('请先在电脑端配置 ComfyUI 的 ' + kind + ' 文件夹')
        return libraries[kind]

    async def listing(request):
        try:
            result = await asyncio.to_thread(configured(request).listing, request.query.get('path', ''),
                request.query.get('kind', 'all'), request.query.get('search', ''),
                int(request.query.get('offset', '0')))
        except FileNotFoundError:
            return server.response({'error': '文件夹不存在或已被移动'}, 404)
        return server.response(result)

    async def media(request):
        target = configured(request).resolve(request.query.get('path', ''))
        if not target.is_file():
            raise web.HTTPNotFound()
        kind = file_kind(target)
        headers = {'Cache-Control': 'private, no-cache', 'X-Content-Type-Options': 'nosniff'}
        if request.query.get('preview') == '1' and kind in ('image', 'video'):
            stat = target.stat()
            if kind == 'image' and stat.st_size > 80 * 1024 * 1024:
                raise ValueError('图片过大，请直接下载原图')
            cache = server.STATE / 'output-previews'
            cache.mkdir(exist_ok=True)
            key = hashlib.sha256(f'v2:{target}:{stat.st_mtime_ns}:{stat.st_size}'.encode()).hexdigest()
            preview = cache / (key + '.webp')
            async with server.PREVIEW_LOCK:
                if not preview.exists():
                    small = await asyncio.to_thread(video_preview, target) if kind == 'video' else await asyncio.to_thread(lambda: make_preview(target.read_bytes()))
                    await asyncio.to_thread(preview.write_bytes, small)
            return web.FileResponse(preview, headers={**headers, 'Content-Type': 'image/webp'})
        if request.query.get('download') == '1' or kind == 'file':
            import urllib.parse
            headers['Content-Disposition'] = "attachment; filename*=UTF-8''" + urllib.parse.quote(target.name, safe='')
        return web.FileResponse(target, headers=headers)

    app.add_routes([web.get('/api/files', listing), web.get('/api/files/media', media)])
