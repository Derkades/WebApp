#!/bin/bash
set -ex
python3 scanner.py
exec gunicorn -b 0.0.0.0:8080 --workers 4 --threads 4 app