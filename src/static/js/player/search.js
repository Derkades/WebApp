class Search {
    /** @type {HTMLInputElement} */
    #queryInput;

    constructor() {
        eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, () => {
            this.#performSearch();
        });
        this.#queryInput = document.getElementById('search-query');
        this.#queryInput.addEventListener('input', () => this.#performSearch());
    }

    clearSearch() {
        document.getElementById('search-query').value = '';
        document.getElementById('search-result-tracks').replaceChildren();
        document.getElementById('search-result-artists').replaceChildren();
        document.getElementById('search-result-albums').replaceChildren();
    }

    #performSearch() {
        const query = this.#queryInput.value;
        const allTracks = Object.values(state.tracks);

        {
            const tracks = fuzzysort.go(query, allTracks, {keys: ['title', 'path', 'artistsJoined', 'album'], limit: 10}).map(e => e.obj);
            document.getElementById('search-result-tracks').replaceChildren(browse.generateTrackList(tracks));
        }

        {
            const results = fuzzysort.go(query, allTracks, {key: 'artistsJoined', limit: 5});
            const tracks = results.map(e => e.obj);

            const table = document.createElement('table');
            const listedArtists = new Set();
            for (const track of tracks) {
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
            document.getElementById('search-result-artists').replaceChildren(table);
        }

        {
            const tracks = fuzzysort.go(query, allTracks, {keys: ['album', 'albumArtist', 'artistsJoined'], limit: 5}).map(e => e.obj);
            const newChildren = [];
            const listedAlbums = new Set();
            for (const track of tracks) {
                if (listedAlbums.has(track.album)) {
                    continue;
                }
                listedAlbums.add(track.album);

                const imgUri = `/get_album_cover?quality=low&path=${encodeURIComponent(track.path)}`
                const img = document.createElement('div');
                img.style.display = 'inline-block';
                img.style.margin = '.5rem';
                img.style.height = '16rem';
                img.style.width = '16rem';
                img.style.borderRadius = 'var(--border-radius-amount)';
                img.style.background = `url("${imgUri}") no-repeat center`;
                img.style.backgroundSize = 'cover';
                img.onclick = () => browse.browseAlbum(track.album, track.albumArtist);

                newChildren.push(img);

            }
            document.getElementById('search-result-albums').replaceChildren(...newChildren);
        }
    }
}

const search = new Search();

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('open-dialog-search').addEventListener('click', () => {
        search.clearSearch();
    })
});
