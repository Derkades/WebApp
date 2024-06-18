# pylint: disable=invalid-name

from os import getenv
from pathlib import Path
from typing import Optional

# Hardcoded settings
csrf_validity_seconds = 3600
app_dir = Path(__file__).parent.resolve()
static_dir = app_dir / 'static'
migration_sql_dir = app_dir / 'migrations'
init_sql_dir = app_dir / 'sql'
raphson_png = static_dir / 'img' / 'raphson.png'
user_agent = 'Super-fancy-music-player/2.0 (https://github.com/DanielKoomen/WebApp/)'
user_agent_offline_sync = 'Super fancy music player (offline sync) (https://github.com/DanielKoomen/WebApp/)'
webscraping_user_agent = getenv('MUSIC_WEBSCRAPING_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0')  # https://useragents.me
loudnorm_filter = 'loudnorm=I=-16'

# User configurable settings
music_dir: Path = None
data_dir: Path = None
ffmpeg_log_level: str = None
track_max_duration_seconds: int = None
radio_playlists: list[str] = []
lastfm_api_key: Optional[str] = None
lastfm_api_secret: Optional[str] = None
offline_mode: bool = None
news_server: str = None
