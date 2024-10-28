# Development

## Development using Docker

With docker and docker-compose-plugin installed, run the following command to start a local testing server:
```
docker compose up --build
```

Before doing so, you will need to create a music and data directory. You may need to change `user` in the `compose.yaml` file if your user is not using the default id of 1000.

## Development without Docker

pyproject.toml specifies the project's dependencies, which you [have to install manually](https://github.com/pypa/pip/issues/11440) using pip for now.

Fedora packages, if you prefer (this list may be outdated):
```
sudo dnf install python3-flask python3-flask-babel python3-requests python3-beautifulsoup4 python3-bcrypt yt-dlp babel poedit pylint python3-mypy python3-types-requests python3-types-beautifulsoup4 python3-build twine
```

Start the web server in development mode, which supports live reloading:
```
python3 -m raphson_mp start --dev
```

## Code structure

  * (`data/`): default database directory.
  * `docker/`: additional files used to build containers.
  * `docs/`: documentation in markdown format.
  * (`music/`): default music directory.
  * `raphson_mp/migrations/`: sql files used to update the database.
  * `raphson_mp/routes`: files containing flask blueprints and routes
  * `raphson_mp/sql/`: sql files used to initialize the database, also useful as a database layout reference.
  * `raphson_mp/static/`: static files that are served as-is by the frontend, under the `/static` URL.
  * `raphson_mp/js/player/*.js`: concatenated to `src/js/player.js` on-the-fly, or manually during building for better performance.
  * `raphson_mp/templates/`: jinja2 template files for web pages.
  * `raphson_mp/translations/`: translation files. Do not edit manually, see translations section.
  * `raphson_mp/`: contains program source code
  * `mp.py`: main entrypoint

## Import sorting

Use `isort .` to sort imports.

## Preparing for offline development

### Docker images

Download the base image locally: `docker pull python:3.12-slim`. If you don't do this, buildx will attempt to pull the image very frequently while rebuilding, which won't work offline.

Then, build and start the container: `docker compose up --build`. Following builds will be cached, unless you change one of the `RUN` instructions in the `Dockerfile`.

### Music

Add some music to `./music`. Adding only a small amount is recommended. While online, start the web interface, enable all playlists and skip through all tracks. This will ensure album art and lyrics are downloaded to the cache for all tracks.

## Using babel for translations

In templates:
```jinja
{% trans %}Something in English{% endtrans %}
{{ gettext('Something in English') }}
```

In Python:
```py
from flask_babel import gettext as _

translated_string = _('Something in English')
```

## Translating from English to other languages

1. Run `./update-translations.sh`
2. Edit the `messages.po` file in `src/translations/<language_code>/LC_MESSAGES/` using a text editor or PO editor like Poedit. To create a new language, run: `pybabel init -i messages.pot -d src/translations -l <language_code>`
3. Run `./update-translations.sh` again to ensure the language files are in a consistent format.
