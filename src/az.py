def az_search(title: str) -> Optional[Tuple[str, str, str]]:
    # Geen idee wat dit betekent maar het is nodig
    magic = '1f8269acd39cbe7abcacf17edc4f2221fac2ae2aa786e79129f5023819e9da42'

    r = requests.get('https://search.azlyrics.com/search.php',
                     params={'q': title,
                             'x': magic})
    soup = BeautifulSoup(r.text, 'lxml')
    links = soup.find_all('a')
    for link in links:
        href = link['href']
        if href.startswith('https://www.azlyrics.com/lyrics'):
            children = link.findChildren()
            title = children[1].string[1:-1]
            artist = children[2].string
            return (href, artist, title)
    return None


def az_extract_lyrics(page_url: str) -> List[str]:
    r = requests.get(page_url)
    soup = BeautifulSoup(r.text, 'lxml')
    divs = soup.find_all('div')
    for div in divs:
        if len(div.contents) > 2 and str(div.contents[0]) == '\n' and str(div.contents[1]).startswith('<div class="div-share noprint"'):
            lyrics_div = div.contents[14]
            lyrics = []
            for content in lyrics_div.contents:
                if str(content) != '\n' and \
                   'prohibited by our licensing agreement' not in str(content) and \
                   str(content) != '<br/>':
                    lyrics.append(str(content).strip('\r').strip('\n'))
            return lyrics
    raise ValueError('unexpected response, couldn\'t find lyrics')
