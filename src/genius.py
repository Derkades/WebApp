from typing import Optional, List
import json
import html
import logging
import traceback
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

import cache
import settings


log = logging.getLogger('app.genius')


@dataclass
class Lyrics:
    source_url: Optional[str]
    lyrics: List[str]

    def lyrics_html(self):
        return '<br>\n'.join(self.lyrics)


def _search(title: str) -> Optional[str]:
    """
    Returns: URL of genius lyrics page, or None if no page was found.
    """
    r = requests.get(
        "https://genius.com/api/search/multi",
        params={"per_page": "1", "q": title},
        headers={'User-Agent': settings.webscraping_user_agent}
    )

    search_json = r.json()
    for section in search_json["response"]["sections"]:
        if section['type'] == 'top_hit':
            for hit in section['hits']:
                if hit['index'] == 'song':
                    return hit['result']['url']

    return None


def _extract_lyrics(genius_url: str) -> List[str]:
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
    r = requests.get(genius_url,
                     headers={'User-Agent': settings.webscraping_user_agent})
    text = r.text
    start = text.index('window.__PRELOADED_STATE__ = JSON.parse(') + 41
    end = text.index("}');") + 1
    info_json_string = text[start:end].replace('\\"', "\"").replace("\\'", "'").replace('\\\\', '\\').replace('\\$', '$').replace('\\`', '`')
    try:
        info_json = json.loads(info_json_string)
    except json.decoder.JSONDecodeError as ex:
        log.info('Error retrieving lyrics: json decode error at %s', ex.pos)
        log.info('Neighbouring text: "%s"', info_json_string[ex.pos-20:ex.pos+20])
        raise ex
    lyric_html = info_json['songPage']['lyricsData']['body']['html']
    soup = BeautifulSoup(lyric_html, 'lxml')
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


def get_lyrics(query: str) -> Optional[Lyrics]:
    """
    Search for the given query, then extract lyrics from that page (if found). This function
    will return lyrics from cache if it has been cached before.
    Parameters:
        query: Search query
    Returns: Lyrics object, or None if no lyrics were found
    """
    cache_object = cache.get('genius', query)
    cached_data = cache_object.retrieve_json()

    if cached_data is not None:
        if not cached_data['found']:
            log.info('Returning no lyrics, from cache')
            return None

        log.info('Returning cached lyrics')
        return Lyrics(cached_data['source_url'], cached_data['lyrics'])

    log.info('Searching lyrics: %s', query)
    try:
        genius_url = _search(query)
    except Exception:
        log.info('Search error')
        traceback.print_exc()
        # Return not found now, but don't cache so we try again in the future when the bug is fixed
        return Lyrics(None, ['Error during lyrics search, please report this issue if it persists.'])

    if genius_url is None:
        log.info('No lyrics found')
        cache_object.store_json({'found': False})
        return None

    log.info('Found URL: %s', genius_url)

    try:
        lyrics = _extract_lyrics(genius_url)
    except Exception:
        log.info('Error retrieving lyrics')
        traceback.print_exc()
        # Don't cache so we try again in the future when the bug is fixed
        return Lyrics(genius_url, ['Error retrieving lyrics, please report this issue. Make sure to include the source URL in your report. Please look at the logs for a more detailed message, if you are able to.'])

    cache_object.store_json({
        'found': True,
        'source_url': genius_url,
        'lyrics': lyrics,
    })

    return Lyrics(genius_url, lyrics)
