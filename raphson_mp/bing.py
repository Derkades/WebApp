import json
import logging
import sys
import traceback
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Iterator

import requests
from bs4 import BeautifulSoup

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


def _sort_key_len(download: bytes) -> int:
    return len(download)


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
        soup = BeautifulSoup(r.text, 'lxml')
        results = soup.find_all('a', {'class': 'iusc'})

        # Download multiple images, looking for the image of the largest
        # size (which is probably the highest quality image)

        image_urls = []
        for result in results:
            try:
                # Some images have no 'm' attribute for some reason, skip those.
                m_attr = result['m']
            except KeyError:
                log.info('Skipping result without "m" attribute: %s', result)
                continue

            image_urls.append(json.loads(m_attr)['murl'])

            if len(image_urls) >= 5:
                break

        with ThreadPool(5) as pool:
            maybe_downloads = pool.map(_download, image_urls)

        # Remove failed downloads
        downloads = [d for d in maybe_downloads if d is not None]

        yield from sorted(downloads, key=_sort_key_len)
    except Exception:
        log.info('Error during bing search. This is probably a bug.')
        traceback.print_exc()
        yield from []


if __name__ == '__main__':
    query = sys.argv[1]
    result_bytes = image_search(query)
    if result_bytes is None:
        print('no result found')
        sys.exit(1)

    Path('test_bing_result').write_bytes(result_bytes)
