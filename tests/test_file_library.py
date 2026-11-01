import asyncio
import io
import pathlib
import shutil
import subprocess
import tempfile
import types
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image

from backend.file_library import FileLibrary, install


class FilePaths(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.library = FileLibrary(self.root)

    def test_traversal_drives_and_backslashes_are_rejected(self):
        for path in ('../secret', '/etc/passwd', 'C:/secret', 'file:stream', 'sub\\secret', 'a/../../secret', '\0'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.library.resolve(path)

    def test_filter_search_and_paging_flatten_all_nested_folders(self):
        (self.root/'片段'/'更深一层').mkdir(parents=True)
        (self.root/'视频.mp4').write_bytes(b'video')
        (self.root/'片段'/'更深一层'/'视频.mp4').write_bytes(b'nested video')
        (self.root/'图片.png').write_bytes(b'image')
        result = self.library.listing(kind='video', limit=1)
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['entries'][0]['kind'], 'video')
        self.assertEqual(result['next_offset'], 1)
        self.assertEqual(len(self.library.listing(kind='video',offset=1)['entries']),1)
        self.assertEqual({e['path'] for e in self.library.listing(kind='video')['entries']},
                         {'视频.mp4','片段/更深一层/视频.mp4'})
        self.assertEqual(self.library.listing(search='更深一层')['total'], 1)
        self.assertEqual(self.library.listing(search='图片')['total'], 1)
        self.assertEqual(self.library.listing('片段')['path'], '片段')
        self.assertFalse(any(e['kind']=='folder' for e in self.library.listing()['entries']))

    def test_symlinks_cannot_expose_files_outside_the_root(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.root/'link').symlink_to(outside,target_is_directory=True)
            except OSError:
                self.skipTest('Creating symlinks requires Windows developer mode')
            with self.assertRaises(ValueError): self.library.resolve('link/secret')
            self.assertEqual(self.library.listing()['total'],0)


class FileRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        for name in ('input','output','state'): (self.root/name).mkdir()
        (self.root/'output'/'clip.mp4').write_bytes(b'0123456789')
        (self.root/'input'/'source.wav').write_bytes(b'input')
        (self.root/'output'/'note.html').write_text('<script>bad()</script>')
        server = types.SimpleNamespace(CONF={kind+'_directory':str(self.root/kind) for kind in ('input','output')},
            STATE=self.root/'state',PREVIEW_LOCK=asyncio.Lock(),response=web.json_response)
        app = web.Application()
        install(app,server)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.temp.cleanup()

    async def test_input_and_output_are_independent(self):
        data = await (await self.client.get('/api/files?root=input')).json()
        self.assertEqual([item['name'] for item in data['entries']],['source.wav'])
        self.assertEqual((await self.client.get('/api/files/media?root=input&path=clip.mp4')).status,404)

    async def test_mobile_video_range_and_download(self):
        response = await self.client.get('/api/files/media?path=clip.mp4',headers={'Range':'bytes=2-5'})
        self.assertEqual(response.status,206)
        self.assertEqual(await response.read(),b'2345')
        self.assertEqual(response.headers['Content-Range'],'bytes 2-5/10')
        response = await self.client.get('/api/files/media?path=clip.mp4&download=1')
        self.assertIn('attachment',response.headers['Content-Disposition'])

    async def test_active_documents_are_downloaded_instead_of_rendered(self):
        response = await self.client.get('/api/files/media?path=note.html')
        self.assertIn('attachment',response.headers['Content-Disposition'])
        self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')

    async def test_video_thumbnail_is_a_cached_image(self):
        executable=shutil.which('ffmpeg')
        if not executable: self.skipTest('ffmpeg is not installed')
        target=self.root/'output'/'thumbnail.avi'
        subprocess.run([executable,'-hide_banner','-loglevel','error','-f','lavfi','-i',
            'color=c=blue:s=64x96:r=10:d=0.3','-an','-c:v','mpeg4',str(target)],
            check=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        response=await self.client.get('/api/files/media?path=thumbnail.avi&preview=1')
        self.assertEqual(response.status,200)
        self.assertEqual(response.headers['Content-Type'],'image/webp')
        raw=await response.read()
        with Image.open(io.BytesIO(raw)) as image:
            self.assertEqual(image.format,'WEBP')
            self.assertAlmostEqual(image.width/image.height,64/96,places=2)
        cached=list((self.root/'state'/'output-previews').glob('*.webp'))
        self.assertEqual(len(cached),1)
        stamp=cached[0].stat().st_mtime_ns
        response=await self.client.get('/api/files/media?path=thumbnail.avi&preview=1')
        self.assertEqual(await response.read(),raw)
        self.assertEqual(cached[0].stat().st_mtime_ns,stamp)


if __name__ == '__main__': unittest.main()
