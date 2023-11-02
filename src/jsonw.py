import json
from typing import Any
from datetime import datetime

from flask import Response


def to_json(obj: Any) -> str:
    return json.dumps(obj, allow_nan=False, separators=(',', ':'))


def json_response(obj: Any, last_modified: datetime = None) -> Response:
    response = Response(to_json(obj), content_type='application/json')
    if last_modified:
        response.last_modified = last_modified
        response.cache_control.no_cache = True  # always revalidate cache
    return response


def from_json(json_str: str) -> Any:
    return json.loads(json_str)
