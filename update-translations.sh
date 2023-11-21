#!/bin/bash
set -e
cd app
pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .
pybabel update -i messages.pot -d translations
