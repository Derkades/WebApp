# Manage

The music player provides a `manage` command for management.

## User management

Help:
```
docker compose exec music manage --help
```

Add an example admin user (prompts for password):
```
docker compose exec music manage useradd --admin example
```

Give user write access to a playlist
```
docker compose exec music manage playlist <username> <playlist>
```
