# Databases

The application stores data using several SQLite databases in `/data`.

It is recommended to vacuum the databases every few months. You can do this using the `vacuum` subcommand of the [management program](./manage.md). Note that this process can take a long time and must not be aborted.

## `music.db`

This is the main database. All important data is stored here, like accounts, settings, playback history, and an index of music files and metadata. It should not get larger than a few megabytes.

## `cache.db`

The cache database is used to store the result of expensive operations. For example, it stores transcoded audio, lyrics, album cover images and thumbnails. Its size is usually in the same order of magnitude as the size of your music library, but it may be more or less depending on your usage.

This databse can be deleted, but it is highly recommended to never delete it and even to include it in your backups. This is because the music player will slow down significantly without a populated cache.

Outdated cache entries are automatically removed, but the database usually won't get smaller unless it is vacuumed.

## `offline.db`

The offline database stores downloaded track data when the music player operates in [offline mode](./offline.md). It is **not** safe to delete this database if you are using the music player in offline mode. If you accidentally lost or deleted this database, run the following command to force all tracks to be downloaded again:
```
sqlite3 data/music.db 'DELETE FROM playlist'
```
