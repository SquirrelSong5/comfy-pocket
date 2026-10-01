"""Contract tests for lightweight image previews.

The preview path receives bytes from an upload and returns a small WebP for
the remote UI.  Every fixture is built in memory so these tests do not depend
on the ComfyUI input directory or on a particular machine's files.
"""

from __future__ import annotations

import io
import pathlib
import sys
import unittest

from PIL import Image


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.previews import make_preview


def image_bytes(
    size: tuple[int, int],
    *,
    mode: str = "RGB",
    format: str = "PNG",
    exif_orientation: int | None = None,
) -> bytes:
    image = Image.new(mode, size)
    if mode == "RGBA":
        image.putpixel((0, 0), (255, 0, 0, 0))
        image.putpixel((size[0] - 1, size[1] - 1), (0, 255, 0, 255))
    else:
        image.putpixel((0, 0), (255, 0, 0))
        image.putpixel((size[0] - 1, size[1] - 1), (0, 255, 0))

    buffer = io.BytesIO()
    if exif_orientation is None:
        image.save(buffer, format=format)
    else:
        exif = Image.Exif()
        exif[274] = exif_orientation
        image.save(buffer, format=format, exif=exif.tobytes())
    return buffer.getvalue()


def decoded_preview(raw: bytes) -> Image.Image:
    return Image.open(io.BytesIO(make_preview(raw)))


class PreviewOutputTest(unittest.TestCase):
    def test_returns_webp(self) -> None:
        preview = make_preview(image_bytes((640, 480)))

        with Image.open(io.BytesIO(preview)) as decoded:
            self.assertEqual(decoded.format, "WEBP")

    def test_large_image_is_bounded_to_1280_pixels_without_changing_aspect_ratio(self) -> None:
        decoded = decoded_preview(image_bytes((3000, 2000)))

        self.assertLessEqual(decoded.width, 1280)
        self.assertLessEqual(decoded.height, 1280)
        self.assertAlmostEqual(decoded.width / decoded.height, 3000 / 2000, places=2)
        self.assertEqual(decoded.size, (1280, 853))

    def test_small_image_is_not_upscaled(self) -> None:
        decoded = decoded_preview(image_bytes((640, 480)))

        self.assertEqual(decoded.size, (640, 480))

    def test_portrait_and_wide_aspect_ratios_are_preserved(self) -> None:
        for size in ((2000, 3000), (3000, 1000)):
            with self.subTest(size=size):
                decoded = decoded_preview(image_bytes(size))
                self.assertLessEqual(decoded.width, 1280)
                self.assertLessEqual(decoded.height, 1280)
                self.assertAlmostEqual(decoded.width / decoded.height, size[0] / size[1], places=2)

    def test_exif_orientation_is_applied_and_exif_is_removed(self) -> None:
        # Orientation 6 means rotate 90 degrees clockwise.  A 2x3 source
        # therefore becomes 3x2 after orientation is applied.
        raw = image_bytes((2, 3), exif_orientation=6)

        decoded = decoded_preview(raw)

        self.assertEqual(decoded.size, (3, 2))
        self.assertEqual(len(decoded.getexif()), 0)

    def test_transparency_is_preserved(self) -> None:
        decoded = decoded_preview(image_bytes((64, 48), mode="RGBA"))

        self.assertIn("A", decoded.mode)
        self.assertEqual(decoded.getpixel((0, 0))[-1], 0)
        self.assertEqual(decoded.getpixel((63, 47))[-1], 255)

    def test_input_bytes_are_not_modified(self) -> None:
        raw = image_bytes((320, 240))
        before = bytes(raw)

        make_preview(raw)

        self.assertEqual(raw, before)

    def test_corrupt_input_raises_friendly_value_error(self) -> None:
        with self.assertRaises(ValueError) as caught:
            make_preview(b"this is not an image")

        message = str(caught.exception).strip()
        self.assertTrue(message)
        self.assertNotIn("cannot identify image file", message.lower())


if __name__ == "__main__":
    unittest.main()
