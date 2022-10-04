import settings


LOGCONFIG_DICT = {
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


def apply():
    """
    Apply dictionary config
    """
    import logging.config  # pylint: disable=import-outside-toplevel
    logging.config.dictConfig(LOGCONFIG_DICT)
