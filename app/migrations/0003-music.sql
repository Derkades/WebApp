-- Migrate playlist table to strict mode

PRAGMA foreign_keys=OFF;
BEGIN;
CREATE TABLE playlist_new (
    path TEXT NOT NULL UNIQUE PRIMARY KEY
) STRICT;
INSERT INTO playlist_new SELECT * FROM playlist;
DROP TABLE playlist;
ALTER TABLE playlist_new RENAME TO playlist;
COMMIT;
