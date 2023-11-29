# pylint: disable=invalid-name

from os import getenv


def split_by_semicolon(inp: str) -> list[str]:
    return [s.strip() for s in inp.split(';') if s.strip() != '']


def _boolenv(name: str) -> bool:
    val = getenv(name, '')
    return val == '1' or bool(val)


csrf_validity_seconds = 3600

user_agent = 'Super-fancy-music-player/2.0 (https://github.com/DanielKoomen/WebApp/)'
user_agent_offline_sync = 'Super fancy music player (offline sync) (https://github.com/DanielKoomen/WebApp/)'
music_dir = getenv('MUSIC_MUSIC_DIR')
data_path = getenv('MUSIC_DATA_PATH')
ffmpeg_loglevel = getenv('MUSIC_FFMPEG_LOGLEVEL', 'error')  # hide unfixable "deprecated pixel format used" warning
log_level = getenv('MUSIC_LOG_LEVEL', 'INFO')
webscraping_user_agent = getenv('MUSIC_WEBSCRAPING_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0')  # https://useragents.me
track_limit_seconds = int(getenv('MUSIC_TRACK_LIMIT_SECONDS', '1200'))
radio_playlists = split_by_semicolon(getenv('MUSIC_RADIO_PLAYLISTS', ''))
lastfm_api_key = getenv('MUSIC_LASTFM_API_KEY', '')
lastfm_api_secret = getenv('MUSIC_LASTFM_API_SECRET', '')
dev: bool = getenv('MUSIC_ENV', 'prod') == 'dev'
proxies_x_forwarded_for: int = int(getenv('MUSIC_PROXIES_X_FORWARDED_FOR', '0'))
offline_mode: bool = _boolenv('MUSIC_OFFLINE_MODE')
short_log_format: bool = _boolenv('MUSIC_SHORT_LOG_FORMAT')

if offline_mode:
    music_dir = '/fake_directory'
