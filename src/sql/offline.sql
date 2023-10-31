CREATE TABLE history (
    timestamp INTEGER NOT NULL, -- Seconds since UNIX epoch
    track TEXT NOT NULL -- Intentionally not a foreign key, so history remains when user is deleted
) STRICT;

CREATE TABLE content (
    path TEXT NOT NULL UNIQUE PRIMARY KEY,
    music_data BLOB NOT NULL,
    cover_data BLOB NOT NULL,
    lyrics_json TEXT NOT NULL
) STRICT; -- STRICT mode only for new databases, no migration exists for old databases

CREATE TABLE settings (
    key TEXT NOT NULL UNIQUE PRIMARY KEY,
    value TEXT NOT NULL
);
