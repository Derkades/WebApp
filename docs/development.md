# Development

## Development using Docker

With docker and docker-compose-plugin installed, run the following command to start a local testing server:
```
docker compose up --build
```

Before doing so, you will need to create a music and data directory. You may need to change `user` in the `compose.yaml` file if your user is not using the default id of 1000.

## Installing dependencies locally

Installing python and dependencies locally may be useful, for example to get linting and suggestions in your IDE.

```
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt
```

Fedora packages, if you prefer (missing some types packages):
```
sudo dnf install python3-flask python3-flask-babel python3-requests python3-beautifulsoup4 python3-pillow python3-bcrypt yt-dlp babel poedit pylint python3-mypy python3-types-requests python3-types-beautifulsoup4
```

## Code structure

  * (`data/`): default database directory.
  * (`dev/`): temp files during development.
  * `docker/`: additional files used to build containers.
  * `docs/`: documentation in markdown format.
  * (`music/`): default music directory.
  * `src/migrations/`: sql files used to update the database.
  * `src/sql/`: sql files used to initialize the database.
  * `src/static/`: static files that are served as-is by the frontend, under the `/static` URL.
  * `src/js/player/*.js`: concatenated and saved to `src/js/player.js`. This happens when the docker image is built. During development, this file is generated on the fly.
  * `src/templates/`: jinja2 template files for web pages.
  * `src/translations/`: translation files. Do not edit manually, see translations section.
  * `src/`: Python code. Main entrypoint is `app.py`

() In .gitignore

## Import sorting

Use `isort app` to sort imports.

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
