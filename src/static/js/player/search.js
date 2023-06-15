class Search {
    /** @type {HTMLInputElement} */
    #queryInput;
    /** @type {Fuse} */
    #trackFuse;
    /** @type {Fuse} */
    #artistFuse;
    /** @type {Fuse} */
    #albumFuse;

    constructor() {
        eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, () => {
            this.initFuse();
            this.#performSearch();
        });
        this.#queryInput = document.getElementById('search-query');
        this.#queryInput.addEventListener('input', () => this.#performSearch());
    }

    initFuse() {
        const tracks = Object.values(state.tracks);

        this.#trackFuse = new Fuse(tracks, {keys: [
            {name: 'title'},
            {name: 'display'}
        ]});

        this.#artistFuse = new Fuse(tracks, {keys: [
            {name: 'artists'},
            {name: 'albumArtist'}
        ]});

        this.#albumFuse = new Fuse(tracks, {keys: [
            {name: 'album', weight: 2},
            {name: 'albumArtist'}
        ]});
    }

    #performSearch() {
        console.log('Searching');
        const query = this.#queryInput.value;
        const tracks = this.#trackFuse.search(query, {limit: state.maxTrackListSizeSearch}).map(e => e.item.path);

        {
            const results = this.#artistFuse.search(query, {limit: 5}).map(e => e.item);
            const table = document.createElement('table');
            const listedArtists = new Set();
            for (const result of results) {
                for (const artist of result.artists) {
                    if (listedArtists.has(artist)) {
                        continue;
                    }
                    listedArtists.add(artist);
                    const row = document.createElement('tr');
                    const td = document.createElement('td');
                    td.textContent = artist;
                    row.append(td);
                    table.append(row);
                }
            }
            document.getElementById('search-result-artists').replaceChildren(table);
        }

        {
            const results = this.#albumFuse.search(query, {limit: 5}).map(e => e.item);
            const table = document.createElement('table');
            const listedAlbums = new Set();
            for (const result of results) {
                if (listedAlbums.has(result.album)) {
                    continue;
                }
                listedAlbums.add(result.album);

                const imgUri = `/get_album_cover?quality=tiny&path=${encodeURIComponent(result.path)}`
                const img = document.createElement('div');
                img.style.height = '8rem';
                img.style.width = '8rem';
                img.style.borderRadius = 'var(--border-radius-amount)';
                img.style.background = `url("${imgUri}") no-repeat center`;
                img.style.backgroundSize = 'cover';
                const tdCover = document.createElement('td');
                tdCover.append(img);
                const tdText = document.createElement('td');
                tdText.textContent = result.album;
                const row = document.createElement('tr');
                row.append(tdCover, tdText);
                table.append(row);
            }
            document.getElementById('search-result-albums').replaceChildren(table);
        }
    }
}

const search = new Search();

document.addEventListener('DOMContentLoaded', () => {

});
