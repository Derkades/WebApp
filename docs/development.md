# Development

## Development using Docker

With docker and docker-compose-plugin installed, run the following command to start a local testing server:
```
docker compose up --build
```

Before doing so, you will need to create a music and cache directory. You may need to change `user` in the docker compose file if your user is not using the default id of 1000.

## Installing dependencies locally

Installing python and dependencies locally may be useful, for example to get linting and suggestions in your IDE.

### Fedora
Main packages:
```
sudo dnf install python3 pylint python3-mypy python3-requests python3-beautifulsoup4 python3-musicbrainzngs python3-pillow python3-bcrypt
pip3 install quart quart-babel
```
Translations:
```
sudo dnf install babel poedit
```

## Preparing for offline development

### Docker images

Download the base image locally: `docker pull python:3.11`. If you don't do this, buildx will attempt to pull the image very frequently while rebuilding, which won't work offline.

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
