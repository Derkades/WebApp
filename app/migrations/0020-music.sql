BEGIN;
CREATE INDEX idx_history_private ON history(private);
CREATE INDEX idx_history_timestamp ON history(timestamp);
COMMIT;
