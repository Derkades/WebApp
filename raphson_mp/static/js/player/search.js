class Search {
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
        eventBus.subscribe(MusicEvent.METADATA_CHANGE, () => {
            if (!dialogs.isOpen('dialog-search')) {
                console.debug('search: ignore METADATA_CHANGE, search dialog is not open');
                return;
            }
            console.debug('search: search again after receiving METADATA_CHANGE event');
            this.#performSearch(true);
        });

        document.addEventListener('DOMContentLoaded', () => {
            this.#queryInput.addEventListener('input', () => this.#performSearch());

            document.getElementById('open-dialog-search').addEventListener('click', () => {
                /** @type {HTMLInputElement} */
                const queryField = document.getElementById('search-query');
                queryField.value = '';
                setTimeout(() => queryField.focus({focusVisible: true}), 50); // high delay is necessary, I don't know why
                this.#searchResultParent.classList.add('hidden');
            });
        });
    }

    async #performSearch(searchNow = false) {
        // Only start searching after user has finished typing for better performance and fewer network requests
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

        let tracks = [];
        if (query.length > 1) {
            tracks = await music.search(query);
        } else {
            tracks = [];
        }

        if (tracks.length == 0) {
            this.#searchResultParent.classList.add('hidden');
        } else {
            this.#searchResultParent.classList.remove('hidden');
        }

        // Tracks
        {
            this.#searchResultTracks.replaceChildren(await browse.generateTrackList(tracks));
        }

        // Artists
        {
            const table = document.createElement('table');
            const listedArtists = new Set(); // to prevent duplicates, but is not actually used to preserve ordering
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

        // Albums
        {
            const newChildren = [];
            const listedAlbums = new Set();
            for (const track of tracks) {
                // Do not show too many albums, each of them causes an image load
                if (listedAlbums.size > 8) {
                    break;
                }

                if (track.album == null || listedAlbums.has(track.album)) {
                    continue;
                }
                listedAlbums.add(track.album);

                const img = document.createElement('div');
                img.classList.add('search-result-album');
                const imgUri = await track.getCover('low', true);
                img.style.background = `black url("${imgUri}") no-repeat center`;
                img.style.backgroundSize = 'cover';
                img.onclick = () => browse.browseAlbum(track.album, track.albumArtist);

                newChildren.push(img);
            }

            this.#searchResultAlbums.replaceChildren(...newChildren);
        }
    }
}

const search = new Search();
