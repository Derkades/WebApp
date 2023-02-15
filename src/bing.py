import json
import sys
import logging
import traceback
from typing import Optional
import asyncio

import httpx
from bs4 import BeautifulSoup

import cache
import image
import settings

log = logging.getLogger("app.bing")


async def download_and_verify_image(http: httpx.AsyncClient, image_url: str) -> Optional[bytes]:
    log.info('Downloading image: %s', image_url)
    try:
        response = await http.get(image_url,
                                  headers={'User-Agent': settings.webscraping_user_agent})
    except httpx.ConnectError:
        log.info('Connection error to URL %s', image_url)
        return None

    if response.status_code != 200:
        log.info('Status code %s, skipping', response.status_code)
        return None

    img_bytes = response.content

    if not image.check_valid(img_bytes):
        return None

    return img_bytes


async def image_search(bing_query: str) -> Optional[bytes]:
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
    async with httpx.AsyncClient() as http:
        r = await http.get('https://www.bing.com/images/search',
                           headers={'User-Agent': settings.webscraping_user_agent},
                           params={'q': bing_query,
                                   'form': 'HDRSC2',
                                   'first': '1',
                                   'scenario': 'ImageBasicHover'},
                           cookies={'SRCHHPGUSR': 'ADLT=OFF'})  # disable safe search :-)
        soup = BeautifulSoup(r.text, 'lxml')
        results = soup.find_all('a', {'class': 'iusc'})

        # Try all results, looking for the image of the largest size (which is probably the highest quality image)
        # Some images have no 'm' attribute for some reason, skip those.

        image_urls = []
        fallback_urls = []
        for result in results:
            try:
                m_attr = result['m']
            except KeyError:
                log.info('Skipping result without "m" attribute: %s', result)

            image_url: str = json.loads(m_attr)['murl']

            if image_url.endswith('.png'):
                # Album covers are usually jpegs. Avoid .png, otherwise they will always get downloaded due to their higher size
                fallback_urls.append(image_url)
            else:
                image_urls.append(image_url)

            if len(image_urls) >= settings.bing_image_download_count:
                break
        else:
            # Not enough results
            while len(image_urls) < settings.bing_image_download_count:
                image_urls.append(fallback_urls.pop())

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(download_and_verify_image(http, image_url))
                     for image_url in image_urls]

        best_img_bytes = None
        for task in tasks:
            img_bytes = task.result()
            if img_bytes is not None and \
                    (best_img_bytes is None or \
                     len(img_bytes) > len(best_img_bytes)):
                best_img_bytes = img_bytes

        if best_img_bytes is None:
            cache.store(cache_key, b'magic_no_results')
            log.info('No image found')
        else:
            cache.store(cache_key, best_img_bytes)
            log.info('Found image, %.2fMiB', len(best_img_bytes)/1024/1024)

        return best_img_bytes


if __name__ == '__main__':
    import logconfig
    logconfig.apply()

    query = sys.argv[1]
    result_bytes = asyncio.run(image_search(query))
    if result_bytes is None:
        print('no result found')
        sys.exit(1)

    with open('test_bing_result.webp', 'wb') as test_file:
        test_file.truncate(0)
        test_file.write(result_bytes)
