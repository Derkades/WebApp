import logging
import time

from raphson_mp import auth, cache, db, music, settings

log = logging.getLogger(__name__)


def delete_old_trashed_files() -> int:
    """
    Delete trashed files after 30 days.
    """
    count = 0
    for path in music.list_tracks_recursively(settings.music_dir, trashed=True):
        if path.stat().st_ctime < time.time() - 60*60*24*30:
            log.info('Permanently deleting: %s', path.absolute().as_posix())
            path.unlink()
            count += 1
    return count


def cleanup() -> None:
    """
    Main function called by cleanup command. Invokes other cleanup functions
    """
    start_time = time.time()

    with db.connect() as conn:
        count = auth.prune_old_session_tokens(conn)
        log.info('Deleted %s session tokens', count)

        count = conn.execute('DELETE FROM now_playing WHERE timestamp < ?',
                             (time.time() - 300,)).rowcount
        log.info('Deleted %s now playing entries', count)

        count = delete_old_trashed_files()
        log.info('Deleted %s trashed files', count)

    cache.cleanup()

    end_time = time.time()

    if end_time - start_time > 10:
        log.warning('Cache cleanup took quite long. Consider calling the cleanup command more often. Many music player functions are not available while cleanup is running.')
