-- Migrate now playing to strict mode

-- No need to preserve data
DROP TABLE now_playing;

CREATE TABLE now_playing (
    player_id TEXT NOT NULL UNIQUE PRIMARY KEY,
    user INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    track TEXT NOT NULL REFERENCES track(path) ON DELETE CASCADE,
    progress INTEGER NOT NULL,
    paused INTEGER NOT NULL
) STRICT;
