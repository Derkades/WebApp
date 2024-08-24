BEGIN;

CREATE TABLE cache (
    key TEXT NOT NULL UNIQUE PRIMARY KEY,
    data BLOB NOT NULL,
    expire_time INTEGER NOT NULL
) STRICT; -- STRICT mode only for new databases since 2024-08-24, no migration exists for old databases as it would be too expensive

CREATE INDEX idx_cache_expire_time ON cache(expire_time);

COMMIT;
