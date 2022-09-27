from typing import Union, Callable, Optional
from io import BytesIO
from pathlib import Path
import logging

from PIL import Image
import pillow_avif  # register AVIF plugin

import cache


log = logging.getLogger('app.image')

QUALITY_TABLE = {
    'high': {
        'avif': 100,
        'webp': 100,
        'jpeg': 100,
    },
    'low': {
        'avif': 60,
        'webp': 70,
        'jpeg': 70,
    },
    'verylow': {
        'avif': 50,
        'webp': 50,
        'jpeg': 50,
    }
}


def thumbnail(input_img: Union[Path, bytes, Callable], cache_id: str, thumb_format: str, thumb_resolution: int, thumb_quality = 'high') -> bytes:
    """
    Generate thumbnail, making use of cache.
    Parameters:
        input_img: Input image, either a path, image bytes, or a function that returns image bytes.
        cache_id: A cache identifier string to uniquely identify this image. If a cache object exists
                  with this cache id (and the same thumbnail settings), a thumbnail is returned from cache.
        thumb_format: Image format, 'avif' or 'webp'
        thumb_resolution: Thumbnail height and width. Note that the resulting thumbnail may not necessarily be
                          square, it will still have the same aspect ratio as the original image.
    Returns: Compressed thumbnail image bytes.
    """
    thumb_quality_percent = QUALITY_TABLE[thumb_quality][thumb_format]
    cache_id += thumb_format + str(thumb_quality_percent) + str(thumb_resolution)
    cache_obj = cache.get('thumbnail', cache_id)
    cache_data = cache_obj.retrieve()
    if cache_data is not None:
        log.info('Returning thumbnail from cache: %s', cache_id)
        return cache_data

    log.info('Generating thumbnail: %s', cache_id)

    input_bytes: Optional[bytes]

    if isinstance(input_img, Path):
        with open(input_img, 'rb') as inp_img_f:
            input_bytes = inp_img_f.read()
    elif callable(input_img):
        input_bytes = input_img()
    elif isinstance(input_img, bytes):
        input_bytes = input_img
    elif input_img is None:
        log.warning('input_img is None, using fallback for id: %s', cache_id)
        input_bytes = None
    else:
        raise ValueError('invalid image type: ' + type(input_img))

    if input_bytes is not None:
        try:
            img = Image.open(BytesIO(input_bytes))
            img.thumbnail((thumb_resolution, thumb_resolution), Image.ANTIALIAS)
            img_out = BytesIO()
            img.save(img_out, format=thumb_format, quality=thumb_quality_percent)
            img_out.seek(0)
            comp_bytes = img_out.read()

            cache_obj.store(comp_bytes)
            return comp_bytes
        except Exception as ex:
            log.warning('Error during thumbnail generation: %s', ex)

    return thumbnail(Path('static', 'raphson.png'), 'raphson', thumb_format, thumb_resolution)


def check_valid(input_img: bytes) -> bool:
    """
    Ensure an image is valid by loading it with Pillow
    """
    try:
        Image.open(BytesIO(input_img))
        return True
    except Exception as ex:
        log.info('Corrupt image: %s', ex)
        return False