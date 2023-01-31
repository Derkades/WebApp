# Migrations

## 2022-01-27

```sql
ALTER TABLE playlist DROP COLUMN name;
```

```sql
ALTER TABLE track RENAME COLUMN album_index TO track_number;
```

## 2022-01-30
```sql
ALTER TABLE user ADD COLUMN primary_playlist TEXT NULL REFERENCES playlist(path) ON DELETE SET NULL;
```

## 2022-01-31
```sql
ALTER TABLE session RENAME COLUMN last_user_agent TO user_agent;
ALTER TABLE session RENAME COLUMN last_address TO remote_address;
```
