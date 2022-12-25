import json
import sys
import logging
import traceback
from typing import Optional

import requests
from bs4 import BeautifulSoup

import cache
import image
import settings

log = logging.getLogger("app.bing")


def image_search(bing_query: str) -> Optional[bytes]:
    """
    Perform image search using Bing
    Parameters:
        bing_query: Search query
    Returns: Image data bytes
    """

    cache_obj = cache.get('bing', bing_query)
    cache_data = cache_obj.retrieve()
    if cache_data:
        if cache_data == b'magic_no_results':
            log.info('Returning no result, from cache: %s', bing_query)
            return None
        log.info('Returning bing result from cache: %s', bing_query)
        return cache_data

    log.info('Searching bing: %s', bing_query)
    try:
        headers = {'User-Agent': settings.webscraping_user_agent}
        r = requests.get('https://www.bing.com/images/search',
                         timeout=10
                         headers=headers,
                         params={'q': bing_query,
                                 'form': 'HDRSC2',
                                 'first': '1',
                                 'scenario': 'ImageBasicHover'},
                         cookies={'SRCHHPGUSR': 'ADLT=OFF'})  # disable safe search :-)
        soup = BeautifulSoup(r.text, 'lxml')
        results = soup.find_all('a', {'class': 'iusc'})

        # Try all results, looking for the image of the largest size (which is probably the highest quality image)
        # Some images have no 'm' attribute for some reason, skip those.

        max_consider_images = 5
        best_image = None
        for result in results:
            try:
                m_attr = result['m']
            except KeyError:
                log.info('Skipping result without "m" attribute: %s', result)

            image_url = json.loads(m_attr)['murl']

            log.info('Downloading image (%s left): %s', max_consider_images, image_url)

            try:
                resp = requests.get(image_url,
                                    timeout=10,
                                    headers=headers)
                if resp.status_code != 200:
                    log.info('Status code %s, skipping', resp.status_code)
                    continue
                img_bytes = resp.content

                if not image.check_valid(img_bytes):
                    continue

                if best_image is None or len(img_bytes) > len(best_image):
                    best_image = img_bytes

                max_consider_images -= 1
                if max_consider_images == 0:
                    break
            except Exception as ex:
                log.info('Exception while downloading image, skipping. %s', ex)

        if best_image is None:
            cache_obj.store(b'magic_no_results')
            log.info('No image found')
        else:
            cache_obj.store(best_image)
            log.info('Found image, %.2fMiB', len(best_image)/1024/1024)

        return best_image
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

    with open('test_bing_result.webp', 'wb') as test_file:
        test_file.truncate(0)
        test_file.write(result_bytes)
