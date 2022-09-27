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
webscraping_user_agent = getenv('MUSIC_WEBSCRAPING_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0')
data_path = getenv('MUSIC_DATA_PATH', '/data')
scanner_processes = int(getenv('MUSIC_SCANNER_PROCESSES', '6'))
