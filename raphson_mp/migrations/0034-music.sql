-- Switch from trigram to unicode61 tokenizer

BEGIN;

DROP TABLE track_fts;

CREATE VIRTUAL TABLE track_fts USING fts5 (
    path,
    title,
    album,
    album_artist,
    artists,
    tokenize='unicode61 remove_diacritics 2' -- https://sqlite.org/fts5.html#unicode61_tokenizer
);

INSERT INTO track_fts SELECT path, title, album, album_artist, GROUP_CONCAT(artist, ' ') FROM track LEFT JOIN track_artist ON path = track GROUP BY path;

COMMIT;
