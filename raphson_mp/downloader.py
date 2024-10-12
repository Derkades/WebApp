import logging
import os
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Generator

from yt_dlp import DownloadError, YoutubeDL

from raphson_mp import settings

log = logging.getLogger(__name__)


if settings.offline_mode:
    # Module must not be imported to ensure no data is ever downloaded in offline mode.
    raise RuntimeError('Cannot use downloader in offline mode')


OPTIONS = {
    'cachedir': '/tmp/yt-dlp-cache',
    'paths': {'temp': '/tmp/yt-dlp-temp'},
    'color': {'stdout': 'never', 'stderr': 'never'},
}


@dataclass
class YtDone:
    status_code: int


class YtQueueLogger:
    queue: Queue  # contains log strings or YtDone object to indicate yt-dlp has finished

    def __init__(self) -> None:
        self.queue = Queue()

    def debug(self, msg: str) -> None:
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            pass
        else:
            self.info(msg)

    def info(self, msg: str) -> None:
        self.queue.put(msg + '\n')
        log.info(msg)
        self.queue.join()

    def warning(self, msg: str) -> None:
        self.queue.put(msg + '\n')
        log.warning(msg)
        self.queue.join()

    def error(self, msg: str) -> None:
        self.queue.put(msg + '\n')
        log.error(msg)
        self.queue.join()

    def done(self, status_code: int) -> None:
        self.queue.put(YtDone(status_code))


def download(download_to: Path, url: str) -> Generator[str, None, int]:
    logger = YtQueueLogger()

    yt_opts = {
        **OPTIONS,
        'format': 'bestaudio',
        'noplaylist': True,
        'postprocessors': [
            {
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'webm>ogg/mp3>mp3/mka'
            }
        ],
        'logger': logger
    }

    def download_thread() -> None:
        os.chdir(download_to)
        with YoutubeDL(yt_opts) as ytdl:
            try:
                status_code = ytdl.download([url])
                logger.done(status_code)
            except DownloadError:
                logger.done(1)

    Thread(target=download_thread, daemon=True).start()

    while True:
        next_item = logger.queue.get(True, 30)
        if isinstance(next_item, YtDone):
            return next_item.status_code

        yield next_item
        logger.queue.task_done()


@dataclass
class SearchResult:
    url: str
    title: str
    channel_name: str
    channel_subscribers: str
    view_count: int
    duration: int
    duration_string: str
    upload_date: str


def search(search_query: str, search_type: str = 'ytsearch') -> list[SearchResult]:
    with YoutubeDL({**OPTIONS, 'default_search': search_type}) as ytdl:
        info = ytdl.extract_info(search_query, download=False)
        results = [SearchResult(entry['original_url'],
                                entry['title'],
                                entry['uploader'],
                                entry['channel_follower_count'],
                                entry['view_count'],
                                entry['duration'],
                                entry['duration_string'],
                                entry['upload_date'])
                   for entry in info['entries']]
        return results
