class Browse {
    #history;
    /** @type {Fuse} */
    #fuse;
    /** @type {Array.<Track>} */
    #filteredTracks;
    /** @type {boolean} */
    #hasFilter;
    /** @type {boolean} */
    searchQueryChanged
    constructor() {
        this.#history = [];
        this.searchQueryChanged = false;

        eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, () => {
            if (dialogs.isOpen('dialog-browse')) {
                this.updateFilter();
            }
        });

        setInterval(() => {
            if (this.searchQueryChanged) {
                this.searchQueryChanged = false;
                this.search();
            }
        }, 250);
    };

    setHeader(textContent) {
        document.getElementById('dialog-browse').getElementsByTagName('h3')[0].textContent = textContent;
    };

    setContent(table) {
        if (table === null) {
            document.getElementById('browse-no-content').classList.remove('hidden');
            document.getElementById('browse-content').replaceChildren();
        } else {
            document.getElementById('browse-no-content').classList.add('hidden');
            document.getElementById('browse-content').replaceChildren(table);
        }
    };

    open() {
        dialogs.open('dialog-browse');
    };

    browse(title, filter) {
        document.getElementById('browse-filter-query').value = ''; // Clear previous search query
        this.open();
        this.setHeader(title);
        this.#history.push({
            title: title,
            filter: filter,
        });
        this.updateFilter();
    };

    back() {
        if (this.#history.length < 2) {
            return;
        }
        this.#history.pop();
        this.updateFilter();
    };

    updateFilter() {
        if (this.#history.length === 0) {
            console.warn('Requested browse list update, but there are no entries in history');
            return;
        }

        const current = this.#history[this.#history.length - 1];
        this.setHeader(current.title);

        // Playlist filter (or 'all')
        const playlist = document.getElementById('browse-filter-playlist').value;

        this.#hasFilter = true;
        let filter;
        if (playlist === 'all') {
            if (current.filter === null) {
                // Show all tracks
                filter = () => true;
                this.#hasFilter = false;
            } else {
                // Apply filter to tracks in all playlist
                filter = current.filter;
            }
        } else {
            if (current.filter === null) {
                // Show tracks in specific playlist
                filter = track => track.playlistPath === playlist;
            } else {
                // Apply filter to tracks in specific playlists
                filter = track => current.filter(track) && track.playlistPath === playlist;
            }
        }

        // https://fusejs.io/api/options.html
        const options = {
            keys: [
                {
                    name: 'title',
                    weight: 2,
                },
                {
                    name: 'display',
                },
                {
                    name: 'artists'
                },
                {
                    name: 'albumArtist',
                },
            ],
        };
        this.#filteredTracks = Object.values(state.tracks).filter(filter)
        this.#fuse = new Fuse(this.#filteredTracks, options);

        this.search();
    }

    search() {
        const query = document.getElementById('browse-filter-query').value.trim().toLowerCase();

        let tracks;
        if (query === ''){
            if (!this.#hasFilter) {
                // No search query, selected playlist, or filter. For performance reasons, don't display entire track list.
                this.setContent(null);
                return;
            }

            // No search query, display all tracks
            tracks = this.#filteredTracks;
        } else {
            const start = performance.now();
            tracks = this.#fuse.search(query, {limit: state.maxTrackListSizeSearch}).map(e => e.item);
            const end = performance.now();
            console.debug(`Search took ${end - start} ms`);
        }

        const start = performance.now();
        const table = this.generateTrackList(tracks);
        const end = performance.now();
        console.debug(`Generating table took ${end - start} ms`);
        this.setContent(table);
    }

    browseArtist(artistName) {
        const artistText = document.getElementById('trans-artist').textContent;
        this.browse(artistText + artistName, track => track.artists !== null && track.artists.indexOf(artistName) !== -1);
    };

    browseAlbum(albumName, albumArtistName) {
        const albumText = document.getElementById('trans-album').textContent;
        const title = albumArtistName === null ? albumName : albumArtistName + ' - ' + albumName;
        this.browse(albumText + title, track => track.album === albumName && track.albumArtist === albumArtistName);
    };

    browseTag(tagName) {
        const tagText = document.getElementById('trans-tag').textContent;
        this.browse(tagText + tagName, track => track.tags.indexOf(tagName) !== -1)
    };

    /**
     * @param {string} playlistName
     */
    browsePlaylist(playlistName) {
        document.getElementById('browse-filter-playlist').value = playlistName;
        this.browseAll();
    };

    browseAll() {
        const allText = document.getElementById('trans-all-tracks').textContent;
        this.browse(allText, null);
    };

    /**
     * @param {Array<Track>} tracks
     */
    generateTrackList(tracks) {
        const table = document.createElement('table');
        table.classList.add('track-list-table');
        const headerRow = document.createElement('tr');
        table.appendChild(headerRow);
        const hcolPlaylist = document.createElement('th');
        const hcolDuration = document.createElement('th');
        const hcolTitle = document.createElement('th');
        const hcolAddTop = document.createElement('th');
        const hcolAddBottom = document.createElement('th');
        const hcolEdit = document.createElement('th')
        headerRow.replaceChildren(hcolPlaylist, hcolDuration, hcolTitle, hcolAddTop, hcolAddBottom, hcolEdit);

        for (const track of tracks) {
            const colPlaylist = document.createElement('td');
            colPlaylist.textContent = track.playlistPath;

            const colDuration = document.createElement('td');
            colDuration.append(secondsToString(track.duration));

            const colTitle = document.createElement('td');
            colTitle.replaceChildren(track.displayHtml());

            const colAddTop = document.createElement('td');
            const addTopButton = createIconButton('playlist-plus.svg', ['vflip']);
            addTopButton.onclick = () => track.downloadAndAddToQueue(true);
            colAddTop.replaceChildren(addTopButton);

            const colAddBottom = document.createElement('td');
            const addButton = createIconButton('playlist-plus.svg');
            addButton.onclick = () => track.downloadAndAddToQueue();
            colAddBottom.replaceChildren(addButton);

            const colEdit = document.createElement('td');
            if (track.playlist().write) {
                const editButton = createIconButton('pencil.svg');
                editButton.onclick = () => editor.open(track);
                colEdit.replaceChildren(editButton);
            }

            const dataRow = document.createElement('tr');
            dataRow.replaceChildren(colPlaylist, colDuration, colTitle, colAddTop, colAddBottom, colEdit);
            table.appendChild(dataRow);
        }
        return table;
    };
};

const browse = new Browse();

document.addEventListener('DOMContentLoaded', () => {
    // Playlist dropdown
    document.getElementById('browse-filter-playlist').addEventListener('input', () => browse.updateFilter());

    // Search query input
    document.getElementById('browse-filter-query').addEventListener('input', () => browse.searchQueryChanged = true);

    // Button to open browse dialog ("add to queue" button)
    document.getElementById('browse-all').addEventListener('click', () => browse.browseAll());

    // Back button in top left corner of browse window
    document.getElementById('browse-back').addEventListener('click', () => browse.back());
});
