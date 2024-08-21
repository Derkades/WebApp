BEGIN;

CREATE INDEX idx_track_album ON track(album);
CREATE INDEX idx_track_album_artist ON track(album_artist);
CREATE INDEX idx_track_last_chosen ON track(last_chosen);

COMMIT;
