#!/bin/bash
set -e
python db.py
python scanner.py
if [ "$MUSIC_ENV" = "dev" ]
then
    # Docker sends SIGTERM, but Flask only stops on SIGINT
    # Catch TERM and send INT instead.
    _term() {
        kill -INT "$child" 2>/dev/null
    }

    trap _term SIGTERM

    flask --debug run -h 0.0.0.0 -p 8080 &

    child=$!
    wait "$child"
else
    exec gunicorn -b 0.0.0.0:8080 app:app
fi
