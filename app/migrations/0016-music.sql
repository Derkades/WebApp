-- Migrate dislikes to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE dislikes_new (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    UNIQUE(user, track)
) STRICT;

INSERT INTO dislikes_new SELECT * FROM dislikes;

DROP TABLE dislikes;

ALTER TABLE dislikes_new RENAME TO dislikes;

COMMIT;
