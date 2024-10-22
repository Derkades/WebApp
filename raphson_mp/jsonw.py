import json
from datetime import datetime
from typing import Any, Optional

from flask import Response


def to_json(obj: Any) -> str:
    """Convert object to json using json.dumps"""
    return json.dumps(obj, allow_nan=False, separators=(',', ':'))


def json_response(obj: Any, last_modified: Optional[datetime|int] = None) -> Response:
    """Convert object to json, and return as Flask response"""
    response = Response(to_json(obj), content_type='application/json')
    if last_modified:
        response.last_modified = last_modified
        response.cache_control.no_cache = True  # always revalidate cache
    return response


def from_json(json_str: str) -> Any:
    """Read json string to object using json.loads"""
    return json.loads(json_str)
