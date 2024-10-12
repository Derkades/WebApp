-- Make some columns in track_artist table case insensitive

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE track_artist_new (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    artist TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (track, artist)
) STRICT;

INSERT INTO track_artist_new SELECT track, artist FROM track_artist;

DROP TABLE track_artist;

ALTER TABLE track_artist_new RENAME TO track_artist;

COMMIT;
