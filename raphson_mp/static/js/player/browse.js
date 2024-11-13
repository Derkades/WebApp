class BrowseHistoryEntry {
    /** @type {string} */
    title;
    /** @type {object} */
    filters;
    constructor(title, filters) {
        this.title = title;
        this.filters = filters;
    }
}

class Browse {
    /** @type {Array<BrowseHistoryEntry>} */
    #history;
    constructor() {
        this.#history = [];

        eventBus.subscribe(MusicEvent.METADATA_CHANGE, () => {
            if (!windows.isOpen('window-browse')) {
                console.debug('browse: ignore METADATA_CHANGE, browse window is not open. Is editor open: ', windows.isOpen('window-editor'));
                return;
            }

            console.debug('browse: received METADATA_CHANGE, updating content');
            this.updateContent();
        });
    };

    /**
     * @returns {BrowseHistoryEntry}
     */
    current() {
        if (this.#history.length === 0) {
            throw new Exception();
        }

        return this.#history[this.#history.length - 1];
    }

    /**
     * @param {string} textContent
     */
    setHeader(textContent) {
        document.getElementById('window-browse').getElementsByTagName('h2')[0].textContent = textContent;
    };

    /**
     * @param {string} title
     * @param {Array<Filter>} filters
     */
    browse(title, filters) {
        windows.open('window-browse');
        if (!filters.playlist) {
            document.getElementById('browse-filter-playlist').value = 'all';
        }
        this.#history.push(new BrowseHistoryEntry(title, filters));
        this.updateContent();
    };

    back() {
        if (this.#history.length < 2) {
            return;
        }
        this.#history.pop();
        this.updateContent();
    };

    async updateContent() {
        // Remove previous content, while new content is loading
        // TODO loading animation?
        document.getElementById('browse-content').replaceChildren();

        const current = this.current();
        this.setHeader(current.title);

        // update playlist dropdown from current filter
        if (current.filters.playlist) {
            document.getElementById('browse-filter-playlist').value = current.filters.playlist;
        } else {
            document.getElementById('browse-filter-playlist').value = 'all';
        }

        console.debug('browse:', current);

        if (Object.keys(current.filters).length > 0) {
            const tracks = await music.filter(current.filters);
            const table = await this.generateTrackList(tracks);
            document.getElementById('browse-no-content').hidden = true;
            document.getElementById('browse-content').replaceChildren(table);
        } else {
            document.getElementById('browse-no-content').hidden = false;
            document.getElementById('browse-content').replaceChildren();
        }
    }

    /**
     * @param {string} artistName
     */
    browseArtist(artistName) {
        this.browse(document.getElementById('trans-artist').textContent + artistName, {'artist': artistName});
    };

    /**
     * @param {string} albumName
     * @param {string} albumArtistName
     */
    browseAlbum(albumName, albumArtistName) {
        const title = document.getElementById('trans-album').textContent + (albumArtistName === null ? '' : albumArtistName + ' - ') + albumName;
        const filters = {'album': albumName}
        if (albumArtistName) {
            filters.album_artist = albumArtistName;
        }
        this.browse(title, filters);
    };

    /**
     * @param {string} tagName
     */
    browseTag(tagName) {
        this.browse(document.getElementById('trans-tag').textContent + tagName, {'tag': tagName})
    };

    /**
     * @param {string} playlistName
     */
    browsePlaylist(playlistName) {
        this.browse(document.getElementById('trans-playlist').textContent + playlistName, {playlist: playlistName})
    };

    browseButton() {
        this.browse(document.getElementById('trans-browse').textContent, {});
    };

    /**
     * also used by search.js
     * @param {Array<Track>} tracks
     * @returns {Promise<HTMLTableElement>}
     */
    async generateTrackList(tracks) {
        const table = document.createElement('table');
        table.style.width = '100%';
        const headerRow = document.createElement('tr');
        table.appendChild(headerRow);
        const hcolPlaylist = document.createElement('th');
        const hcolDuration = document.createElement('th');
        const hcolTitle = document.createElement('th');
        const hcolAdd = document.createElement('th');
        const hcolEdit = document.createElement('th')
        headerRow.replaceChildren(hcolPlaylist, hcolDuration, hcolTitle, hcolAdd, hcolEdit);

        const addButton = createIconButton('playlist-plus');
        const editButton = createIconButton('pencil');

        for (const track of tracks) {
            const colPlaylist = document.createElement('td');
            colPlaylist.textContent = track.playlistName;

            const colDuration = document.createElement('td');
            colDuration.textContent = durationToString(track.duration);

            const colTitle = document.createElement('td');
            colTitle.appendChild(track.displayHtml());

            const addButton2 = addButton.cloneNode(true);
            addButton2.addEventListener('click', async () => {
                replaceIconButton(addButton2, 'loading');
                addButton2.firstChild.classList.add('spinning');
                addButton2.disabled = true;

                try {
                    const downloadedTrack = await track.download(...getTrackDownloadParams());
                    queue.add(downloadedTrack, true);
                } catch (ex) {
                    console.error('browse: error adding track to queue', ex)
                }

                replaceIconButton(addButton2, 'playlist-plus')
                addButton2.firstChild.classList.remove('spinning');
                addButton2.disabled = false;
            });
            const colAdd = document.createElement('td');
            colAdd.appendChild(addButton2);
            colAdd.style.width = '2rem';

            const colEdit = document.createElement('td');
            colEdit.style.width = '2rem';

            if ((await music.playlist(track.playlistName)).write) {
                const editButton2 = editButton.cloneNode(true);
                editButton2.addEventListener('click', () => editor.open(track));
                colEdit.appendChild(editButton2);
            }

            const dataRow = document.createElement('tr');
            dataRow.append(colPlaylist, colDuration, colTitle, colAdd, colEdit);
            table.appendChild(dataRow);
        }
        return table;
    };
};

const browse = new Browse();

document.addEventListener('DOMContentLoaded', () => {
    // Playlist dropdown
    document.getElementById('browse-filter-playlist').addEventListener('input', event => {
        console.debug('browse: filter-playlist input trigger');
        const playlist = event.target.value;
        const current = browse.current();
        // browse again, but with a changed playlist filter
        const newFilter = {...current.filters}
        if (playlist == 'all') {
            delete newFilter.playlist;
        } else {
            newFilter.playlist = playlist;
        }
        browse.browse(current.title, newFilter);
    });

    // Button to open browse window
    document.getElementById('browse-all').addEventListener('click', () => browse.browseButton());

    // Back button in top left corner of browse window
    document.getElementById('browse-back').addEventListener('click', () => browse.back());
});
