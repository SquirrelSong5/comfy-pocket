"""Generate small display assets; originals remain untouched in ComfyUI."""
import io
from PIL import Image,ImageOps,UnidentifiedImageError

def make_preview(raw):
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.width*source.height>80_000_000:raise ValueError('图片过大，无法生成预览')
            im=ImageOps.exif_transpose(source)
            im.thumbnail((1280,1280),Image.Resampling.LANCZOS)
            im=im.convert('RGBA' if 'A' in im.getbands() or 'transparency' in im.info else 'RGB')
            result=io.BytesIO();im.save(result,format='WEBP',quality=82,method=4,exif=b'')
            return result.getvalue()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as e:
        raise ValueError('无法生成图片预览，请下载原图') from e
