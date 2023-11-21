-- Add private column to history table, update to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE history_new (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    user INTEGER NOT NULL,
    track TEXT NOT NULL,
    playlist TEXT,
    private INTEGER NOT NULL
) STRICT;

INSERT INTO history_new SELECT *, 0 FROM history;

DROP TABLE history;

ALTER TABLE history_new RENAME TO history;

COMMIT;
