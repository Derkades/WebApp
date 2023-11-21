-- Migrate offline history table to strict mode, remove playlist column

PRAGMA foreign_keys=OFF;
BEGIN;
CREATE TABLE history_new (
    timestamp INTEGER NOT NULL,
    track TEXT NOT NULL
) STRICT;
INSERT INTO history_new SELECT timestamp, track FROM history;
DROP TABLE history;
ALTER TABLE history_new RENAME TO history;
COMMIT;
