class Search {
    /** @type {HTMLDivElement} */
    #searchResultEmpty = document.getElementById('search-result-empty');
    /** @type {HTMLDivElement} */
    #searchResultParent = document.getElementById('search-result-parent');
    /** @type {HTMLDivElement} */
    #searchResultTracks = document.getElementById('search-result-tracks');
    /** @type {HTMLDivElement} */
    #searchResultArtists = document.getElementById('search-result-artists');
    /** @type {HTMLDivElement} */
    #searchResultAlbums = document.getElementById('search-result-albums');
    /** @type {HTMLInputElement} */
    #queryInput =  document.getElementById('search-query');
    /** @type {number} */
    #searchTimeoutId = null;

    constructor() {
        eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, () => {
            this.#performSearch();
        });
        this.#queryInput.addEventListener('input', () => this.#performSearch());
    }

    clearSearch() {
        this.#searchResultParent.classList.add('hidden');
        this.#searchResultTracks.replaceChildren();
        this.#searchResultArtists.replaceChildren();
        this.#searchResultAlbums.replaceChildren();
        this.#searchResultEmpty.classList.remove('hidden');
    }

    #performSearch(searchNow = false) {
        // Only start searching after user has finished typing for better performance
        if (!searchNow) {
            // Reset timer when new change is received
            if (this.#searchTimeoutId != null) {
                clearTimeout(this.#searchTimeoutId);
            }
            // Perform actual search in 200 ms
            this.#searchTimeoutId = setTimeout(() => this.#performSearch(true), 200);
            return;
        }

        const query = this.#queryInput.value;

        // Don't display any results for short queries
        if (query.length < 3) {
            this.clearSearch();
            return;
        }

        const allTracks = Object.values(music.tracks);

        {
            const tracks = fuzzysort.go(query, allTracks, {keys: ['searchString'], threshold: -10000, limit: 50}).map(e => e.obj);
            this.#searchResultTracks.replaceChildren(browse.generateTrackList(tracks));
        }

        {
            const results = fuzzysort.go(query, allTracks, {key: 'searchString', limit: 5});
            const tracks = results.map(e => e.obj);

            const table = document.createElement('table');
            const listedArtists = new Set();
            for (const track of tracks) {
                if (track.artists == null) {
                    continue;
                }

                for (const artist of track.artists) {
                    if (listedArtists.has(artist)) {
                        continue;
                    }
                    listedArtists.add(artist);

                    const artistLink = document.createElement('a');
                    artistLink.textContent = artist;
                    artistLink.onclick = () => browse.browseArtist(artist);

                    const td = document.createElement('td');
                    td.append(artistLink);
                    const row = document.createElement('tr');
                    row.append(td);
                    table.append(row);
                }
            }
            this.#searchResultArtists.replaceChildren(table);
        }

        {
            const tracks = fuzzysort.go(query, allTracks, {keys: ['searchString'], limit: 5}).map(e => e.obj);
            const newChildren = [];
            const listedAlbums = new Set();
            for (const track of tracks) {
                if (listedAlbums.has(track.album)) {
                    continue;
                }
                listedAlbums.add(track.album);

                const img = document.createElement('div');
                img.classList.add('search-result-album');
                const imgUri = `/track/album_cover?quality=low&path=${encodeURIComponent(track.path)}`;
                img.style.background = `black url("${imgUri}") no-repeat center`;
                img.style.backgroundSize = 'cover';
                img.onclick = () => browse.browseAlbum(track.album, track.albumArtist);

                newChildren.push(img);

            }
            this.#searchResultAlbums.replaceChildren(...newChildren);
        }

        this.#searchResultEmpty.classList.add('hidden');
        this.#searchResultParent.classList.remove('hidden');
    }
}

const search = new Search();

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('open-dialog-search').addEventListener('click', () => {
        document.getElementById('search-query').value = '';
        search.clearSearch();
    })
});
