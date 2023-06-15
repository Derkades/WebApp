from dataclasses import dataclass
import os
from threading import Thread
from queue import Queue
from pathlib import Path
from typing import Generator
import logging

from yt_dlp import YoutubeDL, DownloadError


log = logging.getLogger('app.downloader')


@dataclass
class YtDone:
    status_code: int


class YtQueueLogger:
    q: Queue

    def __init__(self):
        self.q = Queue()

    def debug(self, msg):
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            pass
        else:
            self.info(msg)

    def info(self, msg):
        self.q.put(msg + '\n')
        log.info(msg)
        self.q.join()

    def warning(self, msg):
        self.q.put(msg + '\n')
        log.warning(msg)
        self.q.join()

    def error(self, msg):
        self.q.put(msg + '\n')
        log.error(msg)
        self.q.join()


def download(download_to: Path, url: str) -> Generator[str, None, int]:
    logger = YtQueueLogger()

    yt_opts = {
        'format': 'bestaudio',
        'paths': {'temp': '/tmp'},
        'noplaylist': True,
        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'webm>ogg/mp3>mp3/mka'
            }
        ],
        'logger': logger
    }

    def download_thread():
        os.chdir(download_to)
        with YoutubeDL(yt_opts) as ytdl:
            try:
                status_code = ytdl.download([url])
                logger.q.put(YtDone(status_code))
            except DownloadError:
                logger.q.put(YtDone(1))

    Thread(target=download_thread, daemon=True).start()

    while True:
        next_item = logger.q.get(True, 30)
        if isinstance(next_item, YtDone):
            return next_item.status_code

        yield next_item
        logger.q.task_done()
