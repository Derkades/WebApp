-- Restore index deleted in previous migration

CREATE INDEX IF NOT EXISTS idx_track_playlist ON track(playlist);
