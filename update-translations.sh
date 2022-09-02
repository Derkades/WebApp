#!/bin/bash
set -e
pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .
pybabel update -i messages.pot -d src/translations
# To create new language: pybabel init -i messages.pot -d src/translations -l nl
