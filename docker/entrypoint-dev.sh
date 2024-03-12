#!/bin/bash
set -e

# During development, a volume is mounted into /app. Translations are not
# compiled during build so need to be compiled now.
pybabel compile -d app/translations

exec manage $@
