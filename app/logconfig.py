from pathlib import Path


def get_config_dict(short_log_format: bool, error_log_path: Path | None, log_level: str) -> dict:
    config = {
        'version': 1,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s [%(process)d:%(thread)d] [%(levelname)s] [%(name)s:%(module)s:%(lineno)s] %(message)s',
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
                'formatter': 'short' if short_log_format else 'default',
            },
        },
        'loggers': {
            'gunicorn.error': {
                'level': log_level,
                'handlers': ['stdout', 'errors'],
            },
            'gunicorn.access': {
                'level': log_level,
                'handlers': ['stdout'],
            },
        },
        'root': {
            'level': log_level,
            'handlers': ['stdout', 'errors'],
        },
        'disable_existing_loggers': False,
    }

    if error_log_path:
        config['handlers']['errors'] = {
            'class': 'logging.FileHandler',
            'filename': error_log_path.absolute().as_posix(),
            'level': 'WARNING',
            'formatter': 'detailed',
        }

    return config


def apply(logconfig_dict: dict) -> None:
    """
    Apply dictionary config
    """
    import logging.config  # pylint: disable=import-outside-toplevel
    logging.config.dictConfig(logconfig_dict)


def apply_debug() -> None:
    apply(get_config_dict(False, None, 'DEBUG'))
