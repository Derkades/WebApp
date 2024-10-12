-- Make some columns in track_tag table case insensitive

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE track_tag_new (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    tag TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (track, tag)
) STRICT;

INSERT INTO track_tag_new SELECT track, tag FROM track_tag;

DROP TABLE track_tag;

ALTER TABLE track_tag_new RENAME TO track_tag;

COMMIT;
