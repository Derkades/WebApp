BEGIN;

CREATE TABLE IF NOT EXISTS cache (
    key TEXT NOT NULL UNIQUE PRIMARY KEY,
    data BLOB NOT NULL,
    update_time INTEGER NOT NULL,
    access_time INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cache_access_time ON cache(access_time);

COMMIT;
