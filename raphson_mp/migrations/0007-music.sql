BEGIN;

CREATE TABLE user_playlist_favorite (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    UNIQUE(user, playlist)
) STRICT;

INSERT INTO user_playlist_favorite SELECT user, playlist FROM user_playlist WHERE favorite=1;

CREATE TABLE user_playlist_write (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    UNIQUE(user, playlist)
) STRICT;

INSERT INTO user_playlist_write SELECT user, playlist FROM user_playlist WHERE write=1;

DROP TABLE user_playlist;

COMMIT;
