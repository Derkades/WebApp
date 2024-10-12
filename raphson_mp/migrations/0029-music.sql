-- Make some columns in track table case insensitive

PRAGMA foreign_keys=OFF;

BEGIN;

-- Case sensitive indices should be recreated
DROP INDEX idx_track_album;
DROP INDEX idx_track_album_artist;

CREATE TABLE track_new (
    path TEXT NOT NULL UNIQUE PRIMARY KEY,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    duration INTEGER NOT NULL,
    title TEXT NULL COLLATE NOCASE,
    album TEXT NULL COLLATE NOCASE,
    album_artist TEXT NULL COLLATE NOCASE,
    track_number INTEGER NULL,
    year INTEGER NULL,
    mtime INTEGER NOT NULL,
    last_chosen INTEGER NOT NULL DEFAULT 0,
    lyrics TEXT NULL
) STRICT;

INSERT INTO track_new SELECT path, playlist, duration, title, album, album_artist, track_number, year, mtime, last_chosen, lyrics FROM track;

DROP TABLE track;

ALTER TABLE track_new RENAME TO track;

CREATE INDEX idx_track_album ON track(album);
CREATE INDEX idx_track_album_artist ON track(album_artist);

COMMIT;
