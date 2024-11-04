import json
import logging
import traceback
from collections.abc import Iterator
from html.parser import HTMLParser
from multiprocessing.pool import ThreadPool
from typing import override

import requests

from raphson_mp import settings

log = logging.getLogger(__name__)


if settings.offline_mode:
    # Module must not be imported to ensure no data is ever downloaded in offline mode.
    raise RuntimeError('Cannot use bing in offline mode')


def _download(image_url: str) -> bytes | None:
    """
    Download image by URL
    Args:
        image_url
    Returns: Image bytes, or None if the image failed to download
    """
    try:
        resp = requests.get(image_url,
                            timeout=10,
                            headers={'User-Agent': settings.webscraping_user_agent})
        if resp.status_code != 200:
            log.warning('Could not download %s, status code %s', image_url, resp.status_code)
            return None
    except requests.exceptions.RequestException:
        log.warning('Could not download %s, connection error', image_url)
        return None

    img_bytes = resp.content

    log.info('Downloaded image: %s', image_url)

    return img_bytes


def _download_all(image_urls: list[str]) -> Iterator[bytes]:
    """
    Download multiple images, returning the image of the largest size first (probably the
    highest quality image)
    """
    def _sort_key(download: bytes) -> int:
        return len(download)

    with ThreadPool(5) as pool:
        maybe_downloads = pool.map(_download, image_urls)

    # Remove failed downloads
    downloads = [d for d in maybe_downloads if d is not None]

    yield from sorted(downloads, key=_sort_key)


def image_search(bing_query: str) -> Iterator[bytes]:
    """
    Perform image search using Bing
    Parameters:
        bing_query: Search query
    Returns: Image data bytes
    """
    log.info('Searching bing: %s', bing_query)
    try:
        r = requests.get('https://www.bing.com/images/search',
                         timeout=10,
                         headers={'User-Agent': settings.webscraping_user_agent},
                         params={'q': bing_query,
                                 'form': 'HDRSC2',
                                 'first': '1',
                                 'scenario': 'ImageBasicHover'},
                         cookies={'SRCHHPGUSR': 'ADLT=OFF'})  # disable safe search :-)

        r.raise_for_status()

        class Parser(HTMLParser):
            image_urls: list[str] = []

            @override
            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
                if tag != 'a':
                    return

                attrs_dict = dict(attrs)

                if 'class' not in attrs_dict:
                    return

                if attrs_dict['class'] != 'iusc':
                    return

                if 'm' not in attrs_dict:
                    return

                m_attr: str = attrs_dict['m']
                image_url = json.loads(m_attr)['murl']
                self.image_urls.append(image_url)

        parser = Parser()
        parser.feed(r.text)

        yield from _download_all(parser.image_urls[:5])
    except Exception:
        log.info('Error during bing search. This is probably a bug.')
        traceback.print_exc()
        yield from []
