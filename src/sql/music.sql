BEGIN;

CREATE TABLE IF NOT EXISTS playlist (
    path TEXT NOT NULL UNIQUE PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS track (
    path TEXT NOT NULL UNIQUE PRIMARY KEY,
    playlist TEXT NOT NULL,
    duration INTEGER NOT NULL,
    title TEXT NULL,
    album TEXT NULL,
    album_artist TEXT NULL,
    album_index INTEGER NULL,
    year INTEGER NULL,
    mtime INTEGER NOT NULL,
    last_played INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (playlist) REFERENCES playlist(path) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS track_artist (
    track TEXT NOT NULL,
    artist TEXT NOT NULL,
    FOREIGN KEY (track) REFERENCES track(path) ON DELETE CASCADE,
    UNIQUE (track, artist)
);

CREATE TABLE IF NOT EXISTS track_tag (
    track TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (track) REFERENCES track(path) ON DELETE CASCADE,
    UNIQUE (track, tag)
);

CREATE TABLE IF NOT EXISTS radio_track (
    track TEXT NOT NULL,
    start_time INTEGER NOT NULL,
    FOREIGN KEY (track) REFERENCES track(path) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_playlist (
    user INTEGER NOT NULL,
    playlist TEXT NOT NULL,
    favorite INTEGER DEFAULT 0,
    write INTEGER DEFAULT 0,
    UNIQUE (user, playlist),
    FOREIGN KEY (user) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (playlist) REFERENCES playlist(path) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_lastfm (
    user INTEGER NOT NULL UNIQUE PRIMARY KEY,
    name TEXT NOT NULL,
    key TEXT NOT NULL,
    FOREIGN KEY (user) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session (
    user INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    creation_date INTEGER NOT NULL, -- Seconds since UNIX epoch
    last_user_agent TEXT NULL,
    last_address TEXT NULL,
    FOREIGN KEY (user) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS csrf (
    user INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    creation_date INTEGER NOT NULL, -- Seconds since UNIX epoch
    UNIQUE(user, token),
    FOREIGN KEY (user) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL, -- Seconds since UNIX epoch
    user INTEGER NOT NULL, -- Intentionally not a foreign key, so history remains when user is deleted
    track TEXT NOT NULL, -- Intentionally not a foreign key, so history remains when user is deleted
    playlist TEXT -- Could be obtained from track info, but included anyway for convenience
);

CREATE TABLE IF NOT EXISTS now_playing (
    user INTEGER NOT NULL UNIQUE PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    track TEXT NOT NULL,
    FOREIGN KEY (track) REFERENCES track(path) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scanner_log (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL, -- Seconds since UNIX epoch
    action TEXT NOT NULL, -- Literal string 'insert', 'delete', or 'update'
    playlist TEXT NOT NULL, -- Intentionally not a foreign key, log should be kept for deleted playlists
    track TEXT NOT NULL  -- Intentionally not a foreign key, log contains deleted tracks
);

COMMIT;
