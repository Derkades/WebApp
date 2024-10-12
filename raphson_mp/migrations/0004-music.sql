-- Migrate artist and tag tables to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE track_artist_new (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    artist TEXT NOT NULL,
    UNIQUE (track, artist)
) STRICT;

CREATE TABLE track_tag_new (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    UNIQUE (track, tag)
) STRICT;

INSERT INTO track_artist_new SELECT * FROM track_artist;
INSERT INTO track_tag_new SELECT * FROM track_tag;

DROP TABLE track_artist;
DROP TABLE track_tag;

ALTER TABLE track_artist_new RENAME TO track_artist;
ALTER TABLE track_tag_new RENAME TO track_tag;

CREATE INDEX idx_track_artist_track ON track_artist(track);
CREATE INDEX idx_track_tag_track ON track_tag(track);

COMMIT;
