-- Convert radio_track table to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE radio_track_new (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    start_time INTEGER NOT NULL
) STRICT;

INSERT INTO radio_track_new SELECT track, start_time FROM radio_track;

DROP TABLE radio_track;

ALTER TABLE radio_track_new RENAME TO radio_track;

COMMIT;
