"""
Image conversion and thumbnailing
"""
import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

log = logging.getLogger('app.image')


class ImageQuality(Enum):
    HIGH = 'high'
    LOW = 'low'


@dataclass
class ImageParameters:
    quality: int
    resolution: int


QUALITY_PARAMS_TABLE: dict[ImageQuality, ImageParameters] = {
    ImageQuality.HIGH: ImageParameters(95, 1200), # 1200x1200 matches MusicBrainz cover
    ImageQuality.LOW: ImageParameters(70, 512),
}


def webp_thumbnail(input_path: Path, output_path: Path, img_quality: ImageQuality, square: bool):
    quality = QUALITY_PARAMS_TABLE[img_quality].quality
    size = QUALITY_PARAMS_TABLE[img_quality].resolution

    if square:
        thumb_filter = f'scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size}'
    else:
        thumb_filter = f'scale={size}:{size}:force_original_aspect_ratio=decrease'

    subprocess.run(['ffmpeg',
                    '-hide_banner',
                    '-i', input_path.as_posix(),
                    '-pix_fmt', 'yuv420p',
                    '-filter', thumb_filter,
                    '-f', 'webp',
                    '-q', str(quality),
                    output_path.as_posix()],
                   check=True,
                   shell=False)
