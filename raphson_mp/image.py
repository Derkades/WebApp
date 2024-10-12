"""
Image conversion and thumbnailing
"""
import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from raphson_mp import settings

log = logging.getLogger(__name__)


@dataclass
class ImageQuality():
    name: str
    size: int


QUALITY_HIGH = ImageQuality('high', 1200) # 1200x1200 matches MusicBrainz cover
QUALITY_LOW = ImageQuality('low', 512)


class ImageFormat(Enum):
    WEBP = 'webp'
    JPEG = 'jpeg'


def thumbnail(input_path: Path, output_path: Path, img_format: ImageFormat, img_quality: ImageQuality, square: bool):
    size = img_quality.size

    if square:
        thumb_filter = f'scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size}'
    else:
        thumb_filter = f'scale={size}:{size}:force_original_aspect_ratio=decrease'

    if img_format == ImageFormat.WEBP:
        format_options = ['-pix_fmt', 'yuv420p', '-f', 'webp']
    elif img_format == ImageFormat.JPEG:
        format_options = ['-pix_fmt', 'yuvj420p', '-f', 'mjpeg']
    else:
        raise ValueError()

    subprocess.run(['ffmpeg',
                    '-hide_banner',
                    '-nostats',
                    '-loglevel', settings.ffmpeg_log_level,
                    '-i', input_path.as_posix(),
                    '-filter', thumb_filter,
                    *format_options,
                    output_path.as_posix()],
                   check=True,
                   shell=False)
