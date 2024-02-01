# pylint: disable=invalid-name

from os import getenv
from pathlib import Path


def split_by_semicolon(inp: str) -> list[str]:
    return [s.strip() for s in inp.split(';') if s.strip() != '']


def _pathenv(name: str) -> Path:
    path = Path(getenv(name, ''))
    if not path.exists():
        raise ValueError('path does not exist: ' + path.resolve().as_posix())
    return path


def _boolenv(name: str) -> bool:
    val = getenv(name, '')
    return val == '1' or bool(val)


csrf_validity_seconds = 3600
app_dir = Path('app')
static_dir = app_dir / 'static'
migration_sql_dir = app_dir / 'migrations'
init_sql_dir = app_dir / 'sql'
raphson_png = static_dir / 'img' / 'raphson.png'
data_dir = _pathenv('MUSIC_DATA_PATH')

user_agent = 'Super-fancy-music-player/2.0 (https://github.com/DanielKoomen/WebApp/)'
user_agent_offline_sync = 'Super fancy music player (offline sync) (https://github.com/DanielKoomen/WebApp/)'
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
    music_dir = Path('/fake_directory')
else:
    music_dir = _pathenv('MUSIC_MUSIC_DIR')
