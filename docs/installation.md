# Installation

Installation using Docker (or Podman) is currently the only supported way.

Take this example docker compose file as a starting point:

```yaml
version: '3.6'

services:

  music:
    image: ghcr.io/danielkoomen/webapp
    ports:
      - '8080:8080'
    volumes:
      - type: bind
        source: ./music
        target: /music
      - type: bind
        source: ./data
        target: /data
    user: '1000'
    environment:
      TZ: Europe/Amsterdam
```

See [settings.md](settings.md) for a list of environment variables.

After installation, the `manage` command should be used to add users. See [manage.md](./manage.md) for more information.
