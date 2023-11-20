-- Rename never_play to dislikes

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE dislikes (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    UNIQUE(user, track)
);

INSERT INTO dislikes SELECT * FROM never_play;

DROP TABLE never_play;

COMMIT;
