#!/bin/bash
set -e
python db.py
python scanner.py
exec gunicorn -b 0.0.0.0:8080 app
