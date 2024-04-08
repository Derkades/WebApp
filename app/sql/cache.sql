BEGIN;

CREATE TABLE cache (
    key TEXT NOT NULL UNIQUE PRIMARY KEY,
    data BLOB NOT NULL,
    expire_time INTEGER NOT NULL
);

CREATE INDEX idx_cache_expire_time ON cache(expire_time);

COMMIT;
