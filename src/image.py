"""
Image conversion and thumbnailing
"""
from typing import Callable, Optional
from io import BytesIO
from pathlib import Path
import logging
from enum import Enum
from dataclasses import dataclass

from PIL import Image

import cache


log = logging.getLogger('app.image')


class ImageFormat(Enum):
    JPEG = 'jpeg'
    WEBP = 'webp'


class ImageQuality(Enum):
    HIGH = 'high'
    LOW = 'low'


@dataclass
class ThumbnailParameters:
    quality: int
    resolution: int


PARAMS_TABLE: dict[ImageFormat, dict[ImageQuality, ThumbnailParameters]] = {
    ImageFormat.JPEG: {
        ImageQuality.HIGH: ThumbnailParameters(100, 2048),
        ImageQuality.LOW: ThumbnailParameters(50, 512),
    },
    ImageFormat.WEBP: {
        ImageQuality.HIGH: ThumbnailParameters(100, 2048),
        ImageQuality.LOW: ThumbnailParameters(50, 512),
    }
}


def thumbnail(input_img: Path | bytes | Callable,
              cache_key: str,
              img_format: ImageFormat,
              img_quality: ImageQuality,
              square: bool) -> bytes:
    """
    Generate thumbnail, making use of cache.
    Parameters:
        input_img: Input image, either a path, image bytes, or a function that returns image bytes.
        cache_key: A cache identifier string to uniquely identify this image. If a cache object
                   exists with this cache id (and the same thumbnail settings), a thumbnail is
                   returned from cache.
        img_format: Image format, a value from the ImageFormat enum
        img_quality: Image quality, a value from the ImageQuality enum
        square: Whether the thumbnail should be cropped to 1:1 aspect ratio
    Returns: Compressed thumbnail image bytes.
    """
    cache_key += 'thumbnail5' + img_format.value + img_quality.value
    cache_data = cache.retrieve(cache_key)

    if cache_data is not None:
        log.info('Returning thumbnail from cache: %s', cache_key)
        return cache_data

    log.info('Generating thumbnail: %s', cache_key)

    input_bytes: Optional[bytes]

    if isinstance(input_img, Path):
        with open(input_img, 'rb') as inp_img_f:
            input_bytes = inp_img_f.read()
    elif callable(input_img):
        input_bytes = input_img()
    elif isinstance(input_img, bytes):
        input_bytes = input_img
    elif input_img is None:
        log.warning('input_img is None, using fallback for id: %s', cache_key)
        input_bytes = None
    else:
        raise ValueError('invalid image type: ' + type(input_img))

    if input_bytes is not None:
        try:
            params = PARAMS_TABLE[img_format][img_quality]
            img = Image.open(BytesIO(input_bytes))
            img.thumbnail((params.resolution, params.resolution), Image.ANTIALIAS)

            if square:
                new_dim = min(img.height, img.width)

                left = (img.width - new_dim) // 2
                top = (img.height - new_dim) // 2
                right = left + new_dim
                bottom = top + new_dim

                img = img.crop((left, top, right, bottom))

            if img_format == ImageFormat.JPEG and img.mode in {'RGBA', 'P'}:
                # JPEG does not support transparency, remove alpha channel
                img = img.convert('RGB')

            img_out = BytesIO()
            img.save(img_out, format=img_format.value, quality=params.quality)
            img_out.seek(0)
            comp_bytes = img_out.read()

            cache.store(cache_key, comp_bytes)
            return comp_bytes
        except Exception as ex:
            log.warning('Error during thumbnail generation: %s', ex)

    # Return fallback thumbnail if input_bytes was None or an Exception was raised
    fallback_path = Path('static', 'raphson.png')
    if input_img == fallback_path:  # or was this already the fallback cover?
        raise Exception('Error during fallback cover generation')
    return thumbnail(fallback_path, 'raphson', img_format, img_quality, square)


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
