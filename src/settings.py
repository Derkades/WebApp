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


user_agent = 'Super fancy music player (https://github.com/DanielKoomen/WebApp/)'
ffmpeg_loglevel = getenv('MUSIC_FFMPEG_LOGLEVEL', 'info')
music_dir = getenv('MUSIC_MUSIC_DIR', '/music')
log_level = getenv('MUSIC_LOG_LEVEL', 'INFO')
webscraping_user_agent = getenv('MUSIC_WEBSCRAPING_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0')
data_path = getenv('MUSIC_DATA_PATH', '/data')
scanner_processes = int(getenv('MUSIC_SCANNER_PROCESSES', '6'))
track_limit_seconds = int(getenv('MUSIC_TRACK_LIMIT_SECONDS', '600'))
radio_playlists = split_by_semicolon(getenv('MUSIC_RADIO_PLAYLISTS', ''))
radio_announcements_playlist = getenv('MUSIC_RADIO_ANNOUNCEMENTS_PLAYLIST', '')
radio_announcement_chance = 0.2
lastfm_api_key = getenv('MUSIC_LASTFM_API_KEY', '')
lastfm_api_secret = getenv('MUSIC_LASTFM_API_SECRET', '')
