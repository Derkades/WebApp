#!/bin/bash
set -e
python db.py
python scanner.py
if [ "$MUSIC_ENV" = "dev" ]
then
    exec python3 app.py
else
    exec gunicorn -b 0.0.0.0:8080 app:app
fi
