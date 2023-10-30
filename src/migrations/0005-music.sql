-- Migrate user tables to strict mode

PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE user_new (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    nickname TEXT NULL,
    password TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0,
    primary_playlist TEXT NULL REFERENCES playlist(path) ON DELETE SET NULL,
    language TEXT NULL
) STRICT;

CREATE TABLE user_playlist_new (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    favorite INTEGER DEFAULT 0,
    write INTEGER DEFAULT 0,
    UNIQUE (user, playlist)
) STRICT;

CREATE TABLE user_lastfm_new (
    user INTEGER NOT NULL UNIQUE PRIMARY KEY REFERENCES user(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key TEXT NOT NULL
) STRICT;

INSERT INTO user_new SELECT id, username, nickname, password, CAST(admin AS INTEGER), primary_playlist, language FROM user;
INSERT INTO user_playlist_new SELECT * FROM user_playlist;
INSERT INTO user_lastfm_new SELECT * FROM user_lastfm;

DROP TABLE user;
DROP TABLE user_playlist;
DROP TABLE user_lastfm;

ALTER TABLE user_new RENAME TO user;
ALTER TABLE user_playlist_new RENAME TO user_playlist;
ALTER TABLE user_lastfm_new RENAME TO user_lastfm;

CREATE INDEX idx_user_playlist_user ON user_playlist(user);

COMMIT;
