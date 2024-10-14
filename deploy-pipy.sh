#!/usr/bin/env bash
set -e
rm -rf dist
pybabel compile -d raphson_mp/translations
python3 -m build
python3 -m twine upload dist/*
