#!/usr/bin/env bash
set -e
python3 -m build
python3 -m twine upload dist/*
