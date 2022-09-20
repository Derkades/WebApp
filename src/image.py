from typing import Union, Callable
from io import BytesIO
from pathlib import Path
import logging

from PIL import Image
import pillow_avif  # register AVIF plugin

import cache


log = logging.getLogger('app.image')


def thumbnail(input_img: Union[Path, bytes, Callable], cache_id: str, thumb_format: str, thumb_resolution: int) -> bytes:
    """
    Generate thumbnail, making use of cache.
    """
    thumb_quality = 60 if thumb_format == 'avif' else 80
    cache_id += thumb_format + str(thumb_quality) + str(thumb_resolution)
    cache_obj = cache.get('thumbnail', cache_id)
    cache_data = cache_obj.retrieve()
    if cache_data is not None:
        log.info('Returning thumbnail from cache: %s', cache_id)
        return cache_data

    log.info('Generating thumbnail: %s', cache_id)

    if isinstance(input_img, Path):
        with open(input_img, 'rb') as inp_img_f:
            input_img = inp_img_f.read()
    elif callable(input_img):
        input_img = input_img()
    elif isinstance(input_img, bytes):
        pass
    else:
        raise ValueError('invalid image type: ' + type(input_img))

    img = Image.open(BytesIO(input_img))
    img.thumbnail((thumb_resolution, thumb_resolution), Image.ANTIALIAS)
    img_out = BytesIO()
    img.save(img_out, format=thumb_format, quality=thumb_quality)
    img_out.seek(0)
    comp_bytes = img_out.read()

    cache_obj.store(comp_bytes)
    return comp_bytes