from pathlib import Path

from flask_babel import LazyString, lazy_gettext as _

DEFAULT_THEME = 'default'
THEMES: dict[str, LazyString] = {
    'default': _('Default'),
    'win95': _('Windows 95'),
}
