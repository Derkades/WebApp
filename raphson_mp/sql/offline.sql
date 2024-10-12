CREATE TABLE history (
    timestamp INTEGER NOT NULL, -- Seconds since UNIX epoch
    track TEXT NOT NULL
) STRICT;

CREATE TABLE content (
    path TEXT NOT NULL UNIQUE PRIMARY KEY,
    music_data BLOB NOT NULL,
    cover_data BLOB NOT NULL,
    lyrics_json TEXT NOT NULL
) STRICT; -- STRICT mode only for new databases, no migration exists for old databases as it would be too expensive

CREATE TABLE settings (
    key TEXT NOT NULL UNIQUE PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE playlists (
    name TEXT NOT NULL UNIQUE
) STRICT;
