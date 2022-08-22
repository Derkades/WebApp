from typing import Optional
from os import environ as env


def getenv(key: str, default: Optional[str]) -> str:
    if default is None and key not in env:
        raise ValueError('Required environment variable ' + key + ' not configured.')
    return env[key] if key in env else default


web_password = getenv('MUSIC_WEB_PASSWORD', None)
ffmpeg_loglevel = getenv('MUSIC_FFMPEG_LOGLEVEL', 'info')
opus_bitrate = getenv('MUSIC_OPUS_BITRATE', '96K')
max_duration = getenv('MUSIC_MAX_DURATION', '00:08:00')
