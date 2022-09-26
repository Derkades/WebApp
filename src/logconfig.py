import logging.config

import settings

logging.config.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] [%(process)d] [%(levelname)s] [%(module)s] %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': settings.log_level,
        'handlers': ['wsgi']
    },
    'disable_existing_loggers': False,
})
