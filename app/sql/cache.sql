BEGIN;

CREATE TABLE cache2 (
    key TEXT NOT NULL UNIQUE PRIMARY KEY,
    data BLOB NOT NULL,
    expire_time INTEGER NOT NULL
);

CREATE INDEX idx_cache2_expire_time ON cache2(expire_time);

COMMIT;
