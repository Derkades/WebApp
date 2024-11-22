BEGIN;

DROP TABLE settings;

CREATE TABLE settings (
    base_url TEXT NOT NULL,
    token TEXT NOT NULL
) STRICT;

COMMIT;
