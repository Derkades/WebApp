from typing import Optional
import random
import logging

import requests

import settings


log = logging.getLogger('app.reddit')

MEME_SUBREDDITS = [
    'me_irl',
    'meme',
    'memes',
    'ik_ihe',
    'wholesomememes',
    'funny',
]

SUBREDDIT_ATTEMPTS = 3


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
    subreddits = random.choices(MEME_SUBREDDITS, k=SUBREDDIT_ATTEMPTS)
    subreddits.append(None) # If nothing was found, search all of reddit
    for subreddit in subreddits:
        url = _search(subreddit, query)
        if url is not None:
            return url
    return None