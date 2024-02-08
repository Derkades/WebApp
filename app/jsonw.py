import json
from datetime import datetime
from typing import Any, Optional

from flask import Response


def to_json(obj: Any) -> str:
    """Convert object to json using json.dumps"""
    return json.dumps(obj, allow_nan=False, separators=(',', ':'))


def json_response(obj: Any) -> Response:
    """Convert object to json, and return as Flask response"""
    return Response(to_json(obj), content_type='application/json')


def from_json(json_str: str) -> Any:
    """Read json string to object using json.loads"""
    return json.loads(json_str)
