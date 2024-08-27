-- Make CSRF token non nullable

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE session_new (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    csrf_token TEXT NOT NULL,
    creation_date INTEGER NOT NULL,
    user_agent TEXT NULL,
    remote_address TEXT NULL,
    last_use INTEGER NOT NULL
) STRICT;

-- Discard any old sessions that still have a null csrf token. It has been 8 months since
-- the column was added, so legacy sessions without such a token really shouldn't exist
-- anymore.
INSERT INTO session_new SELECT user, token, csrf_token, creation_date, user_agent, remote_address, last_use FROM session WHERE csrf_token IS NOT NULL;

DROP TABLE session;

ALTER TABLE session_new RENAME TO session;

COMMIT;
