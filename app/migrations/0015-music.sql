-- Migrate scanner_log to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE scanner_log_new (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    action TEXT NOT NULL,
    playlist TEXT NOT NULL,
    track TEXT NOT NULL
) STRICT;

INSERT INTO scanner_log_new SELECT * FROM scanner_log;

DROP TABLE scanner_log;

ALTER TABLE scanner_log_new RENAME TO scanner_log;

COMMIT;
