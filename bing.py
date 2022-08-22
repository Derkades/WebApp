import json
import re
import requests
from bs4 import BeautifulSoup


def image_search(bing_query: str) -> bytes:
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
    return r.content


def title_to_query(title: str) -> str:
    print('Original title:', title, flush=True)
    title = title.lower()
    title = title.rstrip('.mp3').rstrip('.webm')  # Remove file extensions
    title = re.sub(r' \[[a-z0-9\-_]+\]', '', title)  # Remove youtube id suffix
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
    title = ''.join([c for c in title if c == ' ' or c == '-' or c >= 'a' and c <= 'z'])  # Remove special characters
    title = title.strip()
    print('Bing title:', title, flush=True)
    return title
