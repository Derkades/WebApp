from typing import Optional
from os import environ as env


def getenv(key: str, default: Optional[str]) -> str:
    """
    Get environment variable. If the environment variable is not set, the
    default value is returned. If no default value is set, an exception
    will be raised.
    """
    if key in env:
        return env[key]
    elif default is not None:
        return default
    else:
        raise ValueError('Required environment variable ' + key + ' not configured.')


web_password = getenv('MUSIC_WEB_PASSWORD', None)
ffmpeg_loglevel = getenv('MUSIC_FFMPEG_LOGLEVEL', 'info')
cache_dir = getenv('MUSIC_CACHE_DIR', '/cache')
music_dir = getenv('MUSIC_MUSIC_DIR', '/music')
log_level = getenv('MUSIC_LOG_LEVEL', 'INFO')
redis_host = getenv('MUSIC_REDIS_HOST', 'localhost')
redis_port = int(getenv('MUSIC_REDIS_PORT', '6379'))
