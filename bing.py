import json
from io import BytesIO
import sys

import requests
from bs4 import BeautifulSoup
from PIL import Image


def webp_thumbnail(data: bytes) -> bytes:
    img = Image.open(BytesIO(data))
    img.thumbnail((1024, 1024), Image.ANTIALIAS)
    img_out = BytesIO()
    img.save(img_out, format='webp', quality=80)
    img_out.seek(0)
    return img_out.read()

def image_search(bing_query: str) -> bytes:
    """
    Perform image search using Bing
    Parameters:
        bing_query: Search query
    Returns: Image data bytes
    """
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
        r = requests.get(img_link, headers=headers, verify=False)
        return webp_thumbnail(r.content)
    raise ValueError('no link with "m" attribute')


if __name__ == '__main__':
    query = sys.argv[1]
    with open('test_bing_result.webp', 'wb') as test_file:
        test_file.truncate(0)
        test_file.write(image_search(query))
