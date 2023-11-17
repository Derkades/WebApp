# Migrations

To run a migration:
1. Shut down the music player (`docker compose stop`)
2. Open the required database using `sqlite3 <database>` (`sqlite3` package on Debian, `sqlite` package on Fedora)
3. Execute the migration by copying it line by line from top to bottom, pressing enter after every line.
4. Exit using <kbd>Ctrl</kbd>+<kbd>D</kbd>

## 2023-10-28
New automatic migration system was introduced. In the future, manual migrations will no longer be required.

`meta.db` (does not exist yet)
```sql
CREATE TABLE db_version (version INTEGER NOT NULL) STRICT;
INSERT INTO db_version VALUES(0);
```

## 2023-09-26
`music.db`
```sql
ALTER TABLE user ADD COLUMN language TEXT NULL;
```

## 2023-08-13
`cache.db`
```sql
DROP TABLE cache;
```

## 2023-07-09
`music.db`
```sql
ALTER TABLE user ADD COLUMN nickname TEXT NULL;
```

## 2023-06-30
`offline.db`
```sql
DROP TABLE settings;
```

## 2023-06-15
`music.db`
```sql
DROP TABLE now_playing;
```

## 2023-04-14
`music.db`
```sql
DROP TABLE now_playing;
```

## 2023-03-14
`music.db`
```sql
BEGIN;
CREATE TABLE session_new (
    user INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    creation_date INTEGER NOT NULL,
    user_agent TEXT NULL,
    remote_address TEXT NULL,
    last_use INTEGER NOT NULL
);
INSERT INTO session_new SELECT user, token, creation_date, user_agent, remote_address, strftime('%s', 'now') FROM session;
DROP TABLE session;
ALTER TABLE session_new RENAME TO session;
COMMIT;
```

## 2023-01-31
`music.db`
```sql
ALTER TABLE session RENAME COLUMN last_user_agent TO user_agent;
ALTER TABLE session RENAME COLUMN last_address TO remote_address;
```

## 2023-01-30
`music.db`
```sql
ALTER TABLE user ADD COLUMN primary_playlist TEXT NULL REFERENCES playlist(path) ON DELETE SET NULL;
```

## 2023-01-27
`music.db`
```sql
ALTER TABLE playlist DROP COLUMN name;
ALTER TABLE track RENAME COLUMN album_index TO track_number;
```
