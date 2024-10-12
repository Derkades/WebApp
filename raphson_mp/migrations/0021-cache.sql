-- Remove old cache table, has been unused for a long time

DROP TABLE IF EXISTS cache;
DROP INDEX IF EXISTS idx_cache_access_time;
