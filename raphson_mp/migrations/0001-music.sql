-- Update track table to strict mode

PRAGMA foreign_keys=OFF;
BEGIN;
CREATE TABLE track_new (
    path TEXT NOT NULL UNIQUE PRIMARY KEY,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    duration INTEGER NOT NULL,
    title TEXT NULL,
    album TEXT NULL,
    album_artist TEXT NULL,
    track_number INTEGER NULL,
    year INTEGER NULL,
    mtime INTEGER NOT NULL,
    last_played INTEGER NOT NULL DEFAULT 0
) STRICT;
INSERT INTO track_new SELECT * FROM track;
DROP TABLE track;
ALTER TABLE track_new RENAME TO track;
COMMIT;
