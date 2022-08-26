from typing import Optional, Tuple, List
import json
import re
import traceback
from io import BytesIO
import html

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


def is_alpha(c):
    return c == ' ' or c == '-' or c >= 'a' and c <= 'z'


def title_to_query(title: str) -> str:
    """
    Simplify track title to be a better bing search query. For example,
    special characters, file extensions and redundant strings like
    "official video" are removed.
    """
    title = title.lower()
    # Remove file extension
    try:
        title = title[:title.rindex('.')]
    except ValueError:
        pass
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


def _az_search(title: str) -> Optional[Tuple[str, str, str]]:
    # Geen idee wat dit betekent maar het is nodig
    magic = '1f8269acd39cbe7abcacf17edc4f2221fac2ae2aa786e79129f5023819e9da42'

    r = requests.get('https://search.azlyrics.com/search.php',
                     params={'q': title,
                             'x': magic})
    soup = BeautifulSoup(r.text, 'html.parser')
    links = soup.find_all('a')
    for link in links:
        href = link['href']
        if href.startswith('https://www.azlyrics.com/lyrics'):
            children = link.findChildren()
            title = children[1].string[1:-1]
            artist = children[2].string
            return (href, artist, title)
    return None


def _az_extract_lyrics(page_url: str) -> List[str]:
    r = requests.get(page_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    divs = soup.find_all('div')
    for div in divs:
        if len(div.contents) > 2 and str(div.contents[0]) == '\n' and str(div.contents[1]).startswith('<div class="div-share noprint"'):
            lyrics_div = div.contents[14]
            lyrics = []
            for content in lyrics_div.contents:
                if str(content) != '\n' and \
                   'prohibited by our licensing agreement' not in str(content) and \
                   str(content) != '<br/>':
                    lyrics.append(str(content).strip('\r').strip('\n'))
            return lyrics
    raise ValueError('unexpected response, couldn\'t find lyrics')


def genius_search(title: str) -> Optional[str]:
    r = requests.get(
        "https://genius.com/api/search/multi",
        params={"per_page": "1", "q": title},
    )

    search_json = r.json()
    for section in search_json["response"]["sections"]:
        if section['type'] == 'top_hit':
            return section['hits'][0]['result']['url']

    return None


def genius_extract_lyrics(genius_url: str) -> List[str]:
    # 1. In de HTML response, zoek voor een stukje JavaScript (een string)
    # 2. Parse deze string als JSON
    # 3. Trek een bepaalde property uit deze JSON, en parse deze met BeautifulSoup weer als HTML
    # 4. Soms staat lyrics in een link of in italics, de for loop maakt dat goed
    r = requests.get(genius_url)
    text = r.text
    start = text.index('window.__PRELOADED_STATE__ = JSON.parse(') + 41
    end = text.index("}');") + 1
    info_json_string = text[start:end].replace('\\"', "\"").replace("\\'", "'").replace('\\\\', '\\').replace('\\$', '$')
    info_json = json.loads(info_json_string)
    lyric_html = info_json['songPage']['lyricsData']['body']['html']
    soup = BeautifulSoup(lyric_html, 'html.parser')
    lyrics = ''
    for content in soup.find('p').contents:
        if content.name == 'a':
            for s in content.contents:
                lyrics += html.escape(str(s).strip())
        elif content.name == 'i':
            for s in content.contents:
                if str(s).strip() == '<br/>':
                    lyrics += html.escape(str(s).strip())
                else:
                    lyrics += '<i>' + html.escape(str(s).strip()) + '</i>'
        else:
            lyrics += html.escape(str(content).strip())

    return lyrics.split('&lt;br/&gt;')
