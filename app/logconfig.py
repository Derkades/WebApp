from typing import Any

from app import settings

FORMATTER = 'short' if settings.short_log_format else 'default'

LOGCONFIG_DICT: dict[str, Any] = {
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s [%(process)d:%(thread)d] [%(levelname)s] [%(module)s:%(lineno)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %Z',
        },
        'default': {
            'format': '%(asctime)s %(levelname)s %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %Z',
        },
        'short': {
            'format': '%(asctime)s %(levelname)s %(name)s: %(message)s',
            'datefmt': '%H:%M:%S',
        }
    },
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': FORMATTER,
        },
        'errors': {
            'class': 'logging.FileHandler',
            'filename': settings.data_dir / 'errors.log',
            'level': 'WARNING',
            'formatter': 'detailed',
        }
    },
    'loggers': {
        'gunicorn.error': {
            'level': settings.log_level,
            'handlers': ['stdout', 'errors'],
        },
        'gunicorn.access': {
            'level': settings.log_level,
            'handlers': ['stdout', 'errors'],
        },
    },
    'root': {
        'level': settings.log_level,
        'handlers': ['stdout', 'errors'],
    },
    'disable_existing_loggers': False,
}


def apply() -> None:
    """
    Apply dictionary config
    """
    import logging.config  # pylint: disable=import-outside-toplevel
    logging.config.dictConfig(LOGCONFIG_DICT)
