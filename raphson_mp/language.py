from flask import request

from raphson_mp import auth, db

LANGUAGES = {
    'en': 'English',
    'nl': 'Nederlands',
}

DEFAULT_LANGUAGE = 'en'


def get_locale() -> str:
    """
    Returns two letter language code, matching a language code in
    the LANGUAGES dict
    """
    try:
        with db.connect(read_only=True) as conn:
            user = auth.verify_auth_cookie(conn)
            if user.language:
                return user.language
    except auth.AuthError:
        pass

    best_match = request.accept_languages.best_match(['nl', 'nl-NL', 'nl-BE', 'en'])
    header_lang = best_match[:2] if best_match else DEFAULT_LANGUAGE
    return header_lang
