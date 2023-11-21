from typing import Any

from app import settings

LOGCONFIG_DICT: dict[str, Any] = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] [%(module)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %Z',
        }
    },
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'default'
        },
    },
    'loggers': {
        'app': {
            'level': settings.log_level,
            'handlers': ['stdout'],
        },
        'gunicorn.error': {
            'level': settings.log_level,
            'handlers': ['stdout'],
        },
        'gunicorn.access': {
            'level': settings.log_level,
            'handlers': ['stdout'],
        },
    },
    'root': {
        'level': settings.log_level,
        'handlers': [],
    },
    'disable_existing_loggers': True,
}


if settings.short_log_format:
    LOGCONFIG_DICT['formatters']['default']['format'] = '%(asctime)s %(levelname)s %(module)s: %(message)s'
    LOGCONFIG_DICT['formatters']['default']['datefmt'] = '%H:%M:%S'


def apply() -> None:
    """
    Apply dictionary config
    """
    import logging.config  # pylint: disable=import-outside-toplevel
    logging.config.dictConfig(LOGCONFIG_DICT)
