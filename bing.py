import json
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from PIL import Image


def webp_thumbnail(data: bytes) -> bytes:
    img = Image.open(BytesIO(data))
    img.thumbnail((700, 700), Image.ANTIALIAS)
    img_out = BytesIO()
    img.save(img_out, format='webp', quality=80)
    img_out.seek(0)
    return img_out.read()


def image_search(bing_query: str) -> bytes:
    """
    Perform image search using Bing
    Parameters:
        bing_query: Search query
    Returns: Image data bytes
    """
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0'}
    r = requests.get('https://www.bing.com/images/search',
                     headers=headers,
                     params={'q': bing_query,
                             'form': 'HDRSC2',
                             'first': '1',
                             'scenario': 'ImageBasicHover'})
    soup = BeautifulSoup(r.text, 'html.parser')
    data = soup.find_all('a', {'class': 'iusc'})[0]
    json_data = json.loads(data['m'])
    img_link = json_data['murl']
    r = requests.get(img_link, headers=headers)
    return webp_thumbnail(r.content)
