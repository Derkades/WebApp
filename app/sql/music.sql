BEGIN;

CREATE TABLE playlist (
    path TEXT NOT NULL UNIQUE PRIMARY KEY
) STRICT;

CREATE TABLE track (
    path TEXT NOT NULL UNIQUE PRIMARY KEY,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    duration INTEGER NOT NULL,
    title TEXT NULL,
    album TEXT NULL,
    album_artist TEXT NULL,
    track_number INTEGER NULL,
    year INTEGER NULL,
    mtime INTEGER NOT NULL,
    last_chosen INTEGER NOT NULL DEFAULT 0,
    lyrics TEXT NULL
) STRICT;

CREATE INDEX idx_track_playlist ON track(playlist);

CREATE TABLE track_artist (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    artist TEXT NOT NULL,
    UNIQUE (track, artist)
) STRICT;

CREATE INDEX idx_track_artist_track ON track_artist(track);

CREATE TABLE track_tag (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    UNIQUE (track, tag)
) STRICT;

CREATE INDEX idx_track_tag_track ON track_tag(track);

CREATE TABLE radio_track (
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    start_time INTEGER NOT NULL
);

CREATE TABLE user (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    nickname TEXT NULL,
    password TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0,
    primary_playlist TEXT NULL REFERENCES playlist(path) ON DELETE SET NULL,
    language TEXT NULL,
    privacy TEXT NULL
) STRICT;

CREATE TABLE user_playlist_favorite (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    UNIQUE (user, playlist)
) STRICT;

CREATE TABLE user_playlist_write (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    playlist TEXT NOT NULL REFERENCES playlist(path) ON DELETE CASCADE,
    UNIQUE(user, playlist)
) STRICT;

CREATE TABLE user_lastfm (
    user INTEGER NOT NULL UNIQUE PRIMARY KEY REFERENCES user(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key TEXT NOT NULL
) STRICT;

CREATE TABLE session (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    csrf_token TEXT NULL, -- For new sesions never null, only legacy sessions have NULL csrf_token (January 2024). In the future, migrate table to NOT NULL and remove legacy code, discarding any old sessions with NULL token.
    creation_date INTEGER NOT NULL, -- Seconds since UNIX epoch
    user_agent TEXT NULL,
    remote_address TEXT NULL,
    last_use INTEGER NOT NULL -- Seconds since UNIX epoch
) STRICT;

CREATE TABLE history (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL, -- Seconds since UNIX epoch
    user INTEGER NOT NULL, -- Intentionally not a foreign key, so history remains when user is deleted
    track TEXT NOT NULL, -- Intentionally not a foreign key, so history remains when user is deleted
    playlist TEXT NOT NULL, -- Could be obtained from track info, but included separately so it is remembered for deleted tracks or playlists
    private INTEGER NOT NULL -- 1 if entry must be hidden from history, only to be included in aggregated data
) STRICT;

CREATE INDEX idx_history_private ON history(private);
CREATE INDEX idx_history_timestamp ON history(timestamp);

CREATE TABLE now_playing (
    player_id TEXT NOT NULL UNIQUE PRIMARY KEY, -- UUID with dashes
    user INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    progress INTEGER NOT NULL, -- Number of seconds into the track
    paused INTEGER NOT NULL
) STRICT;

CREATE TABLE scanner_log (
    id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL, -- Seconds since UNIX epoch
    action TEXT NOT NULL, -- Literal string 'insert', 'delete', or 'update'
    playlist TEXT NOT NULL, -- Intentionally not a foreign key, log may contain deleted playlists. Can be derived from track path, but stored for fast and easy lookup
    track TEXT NOT NULL  -- Intentionally not a foreign key, log may contain deleted tracks
) STRICT;

CREATE TABLE dislikes (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    UNIQUE(user, track)
) STRICT;

CREATE TABLE shares (
    share_code TEXT NOT NULL UNIQUE PRIMARY KEY,
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    create_timestamp INTEGER NOT NULL
) STRICT;

COMMIT;
