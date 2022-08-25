import json
import re
import requests
from io import BytesIO

from bs4 import BeautifulSoup
from PIL import Image


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
    img = Image.open(BytesIO(r.content))
    img.thumbnail((1024, 1024), Image.ANTIALIAS)
    img_out = BytesIO()
    img.save(img_out, format='webp', quality=80)
    img_out.seek(0)
    return img_out.read()


def is_alpha(c):
    return c == ' ' or c == '-' or c >= 'a' and c <= 'z'


def title_to_query(title: str) -> str:
    """
    Simplify track title to be a better bing search query. For example,
    special characters, file extensions and redundant strings like
    "official video" are removed.
    """
    title = title.lower()
    # Remove file extensions
    title = title.rstrip('.mp3').rstrip('.webm')
    # Remove YouTube id suffix
    title = re.sub(r' \[[a-z0-9\-_]+\]', '', title)
    strip_keywords = [
        'monstercat release',
        'nerd nation release',
        'monstercat official music video',
        'official audio',
        'official video',
        'official music video',
        'official lyric video',
        'official hd video',
        'extended version',
        'long version',
        '[out now]',
        'clip officiel',
        'hq videoclip',
        'videoclip',
        '(visual)'
    ]
    for strip_keyword in strip_keywords:
        title = title.replace(strip_keyword, '')
    # Remove special characters
    title = ''.join([c for c in title if is_alpha(c)])
    title = title.strip()
    return title
