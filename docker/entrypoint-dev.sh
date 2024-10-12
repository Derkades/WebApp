#!/bin/bash
set -e

# During development, a volume is mounted into /mp. Translations are not
# compiled during build so need to be compiled now.
pybabel compile -d raphson_mp/translations

exec python3 -m raphson_mp $@
