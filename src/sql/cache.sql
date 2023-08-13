BEGIN;

CREATE TABLE IF NOT EXISTS cache2 (
    key TEXT NOT NULL UNIQUE PRIMARY KEY,
    data BLOB NOT NULL,
    expire_time INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cache2_expire_time ON cache2(expire_time);

COMMIT;
