from gunicorn.app.base import BaseApplication

from app import logconfig, main


class GunicornApp(BaseApplication):
    def __init__(self):
        super().__init__()

    def init(self, parser, opts, args):
        pass

    def load(self):
        return main.app

    def load_config(self):
        self.cfg.set('bind', '0.0.0.0:8080')
        self.cfg.set('worker_class', 'gthread')
        self.cfg.set('workers', 1)
        self.cfg.set('threads', 8)
        self.cfg.set('access_log_format', "%(h)s %(b)s %(M)sms %(m)s %(U)s?%(q)s")
        self.cfg.set('logconfig_dict', logconfig.LOGCONFIG_DICT)
        self.cfg.set('preload_app', True)
        self.cfg.set('timeout', 60)
