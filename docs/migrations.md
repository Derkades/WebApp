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
