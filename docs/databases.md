# Databases

The application stores data using several SQLite databases in `/data`. Files in this directory must never be deleted.

## `music.db`

This is the main database. All important data is stored here, like accounts, settings, playback history, and an index of music files and metadata. It should not get larger than a few megabytes.

## `cache.db`

The cache database is used to store the result of expensive operations. For example, it stores transcoded audio, lyrics, album cover images and thumbnails. The database size varies depending on your usage, but expect it to be around 10GB for every 1000 tracks.

This database, like other databases, must not be deleted.

## `meta.db`

This database stores information about the database version, allowing the app to run the correct database migrations during an upgrade.

## `offline.db`

The offline database stores downloaded track data when the music player operates in [offline mode](./offline.md). It is **not** safe to delete this database. See the [offline mode wiki page](./offline.md) for instructions on how to safely delete downloaded tracks.

## `errors.log`

This is a text file containing all log messages with a `WARNING` level or higher. After acknowledging the warnings, you may empty the file using `truncate -s 0 errors.log`.
