import json
import sys
import logging
import traceback
from typing import Optional
from multiprocessing.pool import ThreadPool

import requests
from bs4 import BeautifulSoup

import cache
import image
import settings

log = logging.getLogger("app.bing")


def _download(image_url: str) -> bytes | None:
    """
    Download image by URL
    Args:
        image_url
    Returns: Image bytes, or None if the image failed to download
    """
    resp = requests.get(image_url,
                        timeout=10,
                        headers={'User-Agent': settings.webscraping_user_agent})
    if resp.status_code != 200:
        log.warning('Could not download %s, status code %s', image_url, resp.status_code)
        return None

    img_bytes = resp.content

    if not image.check_valid(img_bytes):
        log.warning('Could not download %s, image is corrupt', image_url)
        return None

    log.info('Downloaded image: %s', image_url)

    return img_bytes


def _sort_key_len(download: bytes) -> int:
    return len(download)


def image_search(bing_query: str) -> Optional[bytes]:
    """
    Perform image search using Bing
    Parameters:
        bing_query: Search query
    Returns: Image data bytes
    """

    cache_key = 'bing' + bing_query

    cache_data = cache.retrieve(cache_key)
    if cache_data:
        if cache_data == b'magic_no_results':
            log.info('Returning no result, from cache: %s', bing_query)
            return None
        log.info('Returning bing result from cache: %s', bing_query)
        return cache_data

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

            image_urls.append(json.loads(m_attr)['murl'])

            if len(image_urls) >= 5:
                break

        with ThreadPool(5) as pool:
            maybe_downloads = pool.map(_download, image_urls)

        # Remove failed downloads
        downloads = [d for d in maybe_downloads if d is not None]

        if downloads:
            best_image = sorted(downloads, key=_sort_key_len)[-1]
            cache.store(cache_key, best_image)
            log.info('Found image, %.2fMiB', len(best_image)/1024/1024)
            return best_image
        else:
            cache.store(cache_key, b'magic_no_results')
            log.info('No image found')
            return None

    except Exception:
        log.info('Error during bing search. This is probably a bug.')
        traceback.print_exc()
        return None


if __name__ == '__main__':
    query = sys.argv[1]
    result_bytes = image_search(query)
    if result_bytes is None:
        print('no result found')
        sys.exit(1)

    with open('test_bing_result', 'wb') as test_file:
        test_file.truncate(0)
        test_file.write(result_bytes)
