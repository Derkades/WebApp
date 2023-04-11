CREATE TABLE IF NOT EXISTS history (
    timestamp INTEGER NOT NULL, -- Seconds since UNIX epoch
    track TEXT NOT NULL, -- Intentionally not a foreign key, so history remains when user is deleted
    playlist TEXT -- Could be obtained from track info, but included separately so it is remembered for deleted tracks or playlists
);

CREATE TABLE IF NOT EXISTS content (
    path TEXT NOT NULL,
    music_data BLOB NOT NULL,
    cover_data BLOB NOT NULL,
    lyrics_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT NOT NULL,
    value TEXT NOT NULL
);
