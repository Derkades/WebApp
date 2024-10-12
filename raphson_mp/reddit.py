import logging
import random
from typing import Optional

import requests

from raphson_mp import image, settings

log = logging.getLogger(__name__)

MEME_SUBREDDITS = [
    'me_irl',
    'meme',
    'memes',
    'ik_ihe',
    'wholesomememes',
    'wholesomegreentext',
    'greentext',
    'antimeme',
    'misleadingthumbnails',
    'wtfstockphotos',
    'AdviceAnimals',
]

SUBREDDIT_ATTEMPTS = 2


def _search(subreddit: Optional[str], query: str) -> Optional[str]:
    log.info('Searching subreddit %s for: %s', subreddit if subreddit else "ALL", query)

    headers = {'User-Agent': settings.webscraping_user_agent}

    params = {
        'q': query,
        'raw_json': '1',
        'type': 'link',
    }

    if subreddit is None:
        subreddit = 'all' # doesn't matter
    else:
        params['restrict_sr'] = '1'


    r = requests.get(f'https://www.reddit.com/r/{subreddit}/search.json',
                     timeout=10,
                     params=params,
                     headers=headers)

    json = r.json()

    assert json['kind'] == 'Listing'

    posts = json['data']['children']
    for post in posts:
        if post['kind'] == 't3':
            if 'post_hint' in post['data'] and post['data']['post_hint'] == 'image':
                return post['data']['preview']['images'][0]['source']['url']

    return None


def search(query: str) -> Optional[str]:
    """
    Search several subreddits for an image
    Args:
        query: Search query
    Returns: Image URL string, or None if no image was found
    """
    subreddits: list[Optional[str]] = random.choices(MEME_SUBREDDITS, k=SUBREDDIT_ATTEMPTS)
    # subreddits.append(None) # If nothing was found, search all of reddit
    for subreddit in subreddits:
        url = _search(subreddit, query)
        if url is not None:
            return url
    return None


def get_image(query: str) -> Optional[bytes]:
    """
    Search several subreddits for an image, and download it
    Args:
        query: Search query string
    Returns: Downloaded image bytes, or None if no image was found or an error occurred
    """
    image_url = search(query)
    if image_url is None:
        return None

    r = requests.get(image_url,
                     timeout=10,
                     headers={'User-Agent': settings.webscraping_user_agent})

    if r.status_code != 200:
        log.warning('Received status code %s while downloading image from Reddit', r.status_code)
        return None

    image_bytes = r.content

    # if not image.check_valid(image_bytes):
        # return None
    return image_bytes
