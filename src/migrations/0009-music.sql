-- Update csrf table to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE csrf_new (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    creation_date INTEGER NOT NULL, -- Seconds since UNIX epoch
    UNIQUE(user, token)
) STRICT;

INSERT INTO csrf_new SELECT * FROM csrf;

DROP TABLE csrf;

ALTER TABLE csrf_new RENAME TO csrf;

COMMIT;
