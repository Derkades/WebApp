# Settings

The app is configured using environment variables. Below is a list of all environment variables, with their default values and a brief explanation.

## `TZ`

Configure system timezone. You can find a list of valid time zones [on wikipedia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

## `MUSIC_MUSIC_DIR`=`/music`

Music directory. See [music-files.md](./music-files.md)

## `MUSIC_DATA_PATH` (default: `/data`)

This directory is used to store the database files.
- `music.db`: Stores accounts and sessions. Also stores an index of playlist, tracks, and metadata.
- `cache.db`: Stores cached data for slow operations. For example, it stores transcoded audio, downloaded album covers, and scraped lyrics. This database may be deleted, but deleting it will severely impact application performance until it is populated again.