import logging

import db
import auth
import cache


log = logging.getLogger('app.cleanup')


def cleanup():
    with db.connect() as conn:
        count = auth.prune_old_csrf_tokens(conn)
        log.info('Deleted %s old CSRF tokens', count)

        count = auth.prune_old_session_tokens(conn)
        log.info('Deleted %s session tokens', count)

    count = cache.cleanup()
    log.info('Deleted %s entries from cache', count)
