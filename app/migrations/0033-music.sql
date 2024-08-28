-- Triggers created in migration 27 disappeared in migrations 29 and 30 due to an oversight,
-- causing FTS table content to go out of sync. Create them again.

BEGIN;

CREATE TRIGGER track_fts_insert AFTER INSERT ON track BEGIN
    INSERT INTO track_fts (path, title, album, album_artist) VALUES (new.path, new.title, new.album, new.album_artist);
END;

CREATE TRIGGER track_fts_delete AFTER DELETE ON track BEGIN
    DELETE FROM track_fts WHERE path=old.path;
END;

CREATE TRIGGER track_fts_update AFTER UPDATE ON track BEGIN
    UPDATE track_fts SET title = new.title, album = new.album, album_artist = new.album_artist WHERE path = new.path;
END;

CREATE TRIGGER track_fts_artist_insert AFTER INSERT ON track_artist BEGIN
    UPDATE track_fts SET artists = (SELECT GROUP_CONCAT(artist, ' ') FROM track_artist WHERE track=new.track GROUP BY track);
END;

CREATE TRIGGER track_fts_artist_delete AFTER DELETE ON track_artist BEGIN
    UPDATE track_fts SET artists = (SELECT GROUP_CONCAT(artist, ' ') FROM track_artist WHERE track=old.track GROUP BY track);
END;

CREATE TRIGGER track_fts_artist_update AFTER UPDATE ON track_artist BEGIN
    UPDATE track_fts SET artists = (SELECT GROUP_CONCAT(artist, ' ') FROM track_artist WHERE track=new.track GROUP BY track);
END;

-- Ensure content is up-to-date.
DELETE FROM track_fts;
INSERT INTO track_fts SELECT path, title, album, album_artist, GROUP_CONCAT(artist, ' ') FROM track LEFT JOIN track_artist ON path = track GROUP BY path;

COMMIT;
