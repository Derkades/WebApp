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
        const query = this.#queryInput.value;

        {
            const tracks = this.#trackFuse.search(query, {limit: 5}).map(e => e.item);
            document.getElementById('search-result-tracks').replaceChildren(browse.generateTrackList(tracks));
        }

        {
            const tracks = this.#artistFuse.search(query, {limit: 5}).map(e => e.item);
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
            const tracks = this.#albumFuse.search(query, {limit: 5}).map(e => e.item);
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

});
