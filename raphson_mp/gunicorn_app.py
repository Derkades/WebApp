import logging
from typing import Any

from gunicorn.app.base import BaseApplication

from raphson_mp import main

log = logging.getLogger(__name__)


class GunicornApp(BaseApplication):
    bind: str
    proxy_count: int
    logconfig_dict: dict[str, Any]

    def __init__(self, bind: str, proxy_count: int, logconfig_dict: dict[str, Any]):
        self.bind = bind
        self.proxy_count = proxy_count
        self.logconfig_dict = logconfig_dict
        super().__init__()

    def init(self, parser, opts, args):
        pass

    def load(self):
        return main.get_app(proxy_count=self.proxy_count)

    def load_config(self):
        self.cfg.set('bind', self.bind)
        self.cfg.set('worker_class', 'gthread')
        self.cfg.set('workers', 1)
        self.cfg.set('threads', 4)
        self.cfg.set('access_log_format', "%(h)s %(b)s %(M)sms %(m)s %(U)s?%(q)s")
        self.cfg.set('logconfig_dict', self.logconfig_dict)
        self.cfg.set('preload_app', True)
        self.cfg.set('timeout', 60)
