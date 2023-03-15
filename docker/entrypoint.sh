#!/bin/bash
set -e
python db.py
manage scan
manage cleanup

if [ "$MUSIC_ENV" = "dev" ]
then
    # During development, a volume is mounted into /app. This means that the
    # translations compiled during the image build are no longer available and
    # need to be regenerated.
    pybabel compile --statistics -d translations

    exec python3 app.py
else
    exec gunicorn -b 0.0.0.0:8080 app:app
fi
