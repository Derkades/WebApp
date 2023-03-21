from typing import Optional
from os import environ as env


def split_by_semicolon(inp: str) -> list[str]:
    return [s.strip() for s in inp.split(';') if s.strip() != '']


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


def _to_bool(val: str):
    return val == '1' or bool(val)


csrf_validity_seconds = 3600

user_agent = 'Super fancy music player (https://github.com/DanielKoomen/WebApp/)'
ffmpeg_loglevel = getenv('MUSIC_FFMPEG_LOGLEVEL', 'info')
music_dir = getenv('MUSIC_MUSIC_DIR', '/music')
log_level = getenv('MUSIC_LOG_LEVEL', 'INFO')
webscraping_user_agent = getenv('MUSIC_WEBSCRAPING_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0')  # https://useragents.me
data_path = getenv('MUSIC_DATA_PATH', '/data')
track_limit_seconds = int(getenv('MUSIC_TRACK_LIMIT_SECONDS', '900'))
radio_playlists = split_by_semicolon(getenv('MUSIC_RADIO_PLAYLISTS', ''))
lastfm_api_key = getenv('MUSIC_LASTFM_API_KEY', '')
lastfm_api_secret = getenv('MUSIC_LASTFM_API_SECRET', '')
dev: bool = getenv('MUSIC_ENV', 'prod') == 'dev'
proxies_x_forwarded_for: int = int(getenv('MUSIC_PROXIES_X_FORWARDED_FOR', '0'))
offline_mode: bool = _to_bool(getenv('MUSIC_OFFLINE_MODE', ''))
