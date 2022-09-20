import json
from io import BytesIO
import sys
import logging
import traceback
from typing import Optional

import requests
from bs4 import BeautifulSoup
from PIL import Image

import cache


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
        log.info('Returning bing result from cache: %s', bing_query)
        return cache_data

    log.info('Searching bing: %s', bing_query)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0'}
        r = requests.get('https://www.bing.com/images/search',
                        headers=headers,
                        params={'q': bing_query,
                                'form': 'HDRSC2',
                                'first': '1',
                                'scenario': 'ImageBasicHover'},
                        cookies={'SRCHHPGUSR': 'ADLT=OFF'})  # disable safe search :-)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('a', {'class': 'iusc'})
        # Eerst werd hier altijd alleen de eerste gepakt, maar blijkbaar heeft soms de
        # eerste afbeelding geen 'm' attribute. Latere afbeeldingen meestal wel!
        for result in results:
            try:
                json_data = json.loads(result['m'])
            except KeyError:
                continue
            img_link = json_data['murl']
            try:
                resp = requests.get(img_link, headers=headers)
                if resp.status_code != 200:
                    log.info('status code %s, trying next image', r.status_code)
                    continue
                img_bytes = resp.content
                cache_obj.store(img_bytes)
                return img_bytes
            except Exception as ex:
                log.info('exception while downloading image, trying next image. %s', ex)

        raise ValueError('no link with "m" attribute')
    except Exception:
        log.info('No bing results')
        traceback.print_exc()
        return None



if __name__ == '__main__':
    query = sys.argv[1]
    with open('test_bing_result.webp', 'wb') as test_file:
        test_file.truncate(0)
        test_file.write(image_search(query))
