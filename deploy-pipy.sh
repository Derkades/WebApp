#!/usr/bin/env bash
set -e
rm -rf dist
python3 -m build
python3 -m twine upload dist/*
