BEGIN;
DROP INDEX idx_cache2_expire_time;
ALTER TABLE cache2 RENAME TO cache;
CREATE INDEX idx_cache_expire_time ON cache(expire_time);
COMMIT;
