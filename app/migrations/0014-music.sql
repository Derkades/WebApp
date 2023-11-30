-- Migrate session to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE session_new (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    creation_date INTEGER NOT NULL,
    user_agent TEXT NULL,
    remote_address TEXT NULL,
    last_use INTEGER NOT NULL
) STRICT;

INSERT INTO session_new SELECT * FROM session;

DROP TABLE session;

ALTER TABLE session_new RENAME TO session;

COMMIT;
