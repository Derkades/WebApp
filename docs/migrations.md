# Migrations

## 2023-03-14
```
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
```sql
ALTER TABLE session RENAME COLUMN last_user_agent TO user_agent;
ALTER TABLE session RENAME COLUMN last_address TO remote_address;
```

## 2023-01-30
```sql
ALTER TABLE user ADD COLUMN primary_playlist TEXT NULL REFERENCES playlist(path) ON DELETE SET NULL;
```

## 2023-01-27
```sql
ALTER TABLE playlist DROP COLUMN name;
```

```sql
ALTER TABLE track RENAME COLUMN album_index TO track_number;
```
