from typing import Dict
from pathlib import Path
import base64


class Assets:

    def __init__(self):
        self.assets_dir = Path('assets-b64')
        self.assets: Dict[str, str] = {}

        for entry in self.assets_dir.iterdir():
            name = entry.name
            if name.endswith('.svg'):
                mime = 'image/svg+xml'
            elif name.endswith('.woff2'):
                mime = 'font/woff2'
            else:
                raise ValueError('unsupported assets file: ' + name)

            with open(Path(self.assets_dir, name), 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
                self.assets[name] = f'data:{mime};charset=utf-8;base64,{b64}'

    def get_asset_b64(self, name: str) -> str:
        """
        Get asset, css-compatible base64 encoded string
        """
        return self.assets[name]

    def all_assets_dict(self) -> Dict[str, str]:
        """
        Returns: Dictionary of all assets, css base64 encoded
        """
        return self.assets
