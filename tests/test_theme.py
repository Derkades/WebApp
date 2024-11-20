from pathlib import Path
from unittest import TestCase

from raphson_mp.theme import DEFAULT_THEME, THEMES

class TestTheme(TestCase):
    def test_default_theme_exists(self):
        assert DEFAULT_THEME in THEMES

    def test_files_exist(self):
        files = [theme_path.name.rstrip('.css') for theme_path in Path(Path(__file__).parent.parent, 'raphson_mp', 'static', 'css', 'theme').iterdir()]
        for theme in THEMES:
            assert theme in files, 'file does not exist for theme: ' + theme
