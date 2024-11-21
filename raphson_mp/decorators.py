from sqlite3 import Connection
from typing import Any, Callable
from flask import Blueprint, g, request
from flask.typing import ResponseReturnValue, RouteCallable

from raphson_mp import auth, db

def route(bp: Blueprint,
          rule: str | list[str],
          methods: list[str] | None = None,
          public: bool = False,
          require_admin: bool = False,
          skip_csrf_check: bool = False,
          write: bool = False,
          redirect_to_login: bool = False,
          **options: Any) -> Callable[[Callable[..., ResponseReturnValue]], RouteCallable]:
    assert not (public and require_admin), 'cannot be public if admin is required'

    def decorator(func: Callable[..., ResponseReturnValue]) -> RouteCallable:
        def wrapped(*args: Any, **kwargs: Any) -> ResponseReturnValue:
            g.user = None

            if public:
                return func(*args, **kwargs)

            with db.connect(read_only=not write) as conn:
                require_csrf = not skip_csrf_check and request.method == 'POST'
                user = auth.verify_auth_cookie(conn, require_admin=require_admin, require_csrf=require_csrf, redirect_to_login=redirect_to_login)
                g.user = user
                return func(conn, user, *args, **kwargs)

        wrapped.__name__ = func.__name__

        if isinstance(rule, str):
            return bp.route(rule, methods=methods, **options)(wrapped)
        else:
            route: Callable[..., ResponseReturnValue] = wrapped
            for single_rule in rule:
                route = bp.route(single_rule, methods=methods, **options)(route)
            return route

    return decorator
