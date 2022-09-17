from typing import Optional, List
import json
import html

import requests
from bs4 import BeautifulSoup


def search(title: str) -> Optional[str]:
    """
    Returns: URL of genius lyrics page, or None if no page was found.
    """
    r = requests.get(
        "https://genius.com/api/search/multi",
        params={"per_page": "1", "q": title},
    )

    search_json = r.json()
    for section in search_json["response"]["sections"]:
        if section['type'] == 'top_hit':
            for hit in section['hits']:
                if hit['index'] == 'song':
                    return hit['result']['url']

    return None


def extract_lyrics(genius_url: str) -> List[str]:
    """
    Extract lyrics from the supplied Genius lyrics page
    Parameters:
        genius_url: Lyrics page URL
    Returns: A list where each element is one lyrics line.
    """
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


if __name__ == '__main__':
    print(search('Tom Misch & Yussef Dayes - Nightrider (feat. Freddie Gibbs)'))
