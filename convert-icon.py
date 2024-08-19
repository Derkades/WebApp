"""
Place an SVG icon file in the current working directory, or any subdirectory.
Run this script to generate a CSS class for this icon
"""
from base64 import b64encode
from pathlib import Path

for svg_path in sorted(Path().glob('**/*.svg')):
    b64 = b64encode(svg_path.read_bytes())
    print('.icon-' + svg_path.name[:-4] + ' { background-image: url("data:image/svg+xml;charset=utf-8;base64,' + b64.decode() + '"); }')
