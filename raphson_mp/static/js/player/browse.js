class Browse {
    /** @type {Array<object>} */
    #history;
    constructor() {
        this.#history = [];

        eventBus.subscribe(MusicEvent.METADATA_CHANGE, () => {
            if (!dialogs.isOpen('dialog-browse')) {
                console.debug('browse: ignore METADATA_CHANGE, browse window is not open. Is editor open: ', dialogs.isOpen('dialog-editor'));
                return;
            }

            console.debug('browse: received METADATA_CHANGE, updating content');
            this.updateContent();
        });
    };

    /**
     * @param {string} textContent
     */
    setHeader(textContent) {
        document.getElementById('dialog-browse').getElementsByTagName('h2')[0].textContent = textContent;
    };

    open() {
        dialogs.open('dialog-browse');
    };

    /**
     * @param {string} title
     * @param {object} filter
     */
    browse(title, filter) {
        this.setHeader(title);
        this.#history.push({
            title: title,
            filter: filter,
        });
        this.open();
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
        if (this.#history.length === 0) {
            console.warn('browse: requested content update, but there are no entries in history');
            return;
        }

        // Remove previous content, while new content is loading
        // TODO loading animation?
        document.getElementById('browse-content').replaceChildren();

        const current = this.#history[this.#history.length - 1];
        this.setHeader(current.title);

        if (current.filter.playlist) {
            document.getElementById('browse-filter-playlist').value = current.filter.playlist;
        } else {
            document.getElementById('browse-filter-playlist').value = 'all';
        }

        if (Object.keys(current.filter).length > 0) {
            const tracks = await music.filter(current.filter);
            const table = await this.generateTrackList(tracks);
            document.getElementById('browse-no-content').classList.add('hidden');
            document.getElementById('browse-content').replaceChildren(table);
        } else {
            document.getElementById('browse-no-content').classList.remove('hidden');
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
        if (albumArtistName) {
            this.browse(title, {'album_artist': albumArtistName, 'album': albumName});
        } else {
            this.browse(title, {'album': albumName});
        }
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
    browsePlaylist(playlist) {
        this.browse(document.getElementById('trans-playlist').textContent + playlist, {'playlist': playlist})
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
        table.classList.add('track-list-table');
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

            const colEdit = document.createElement('td');

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
    document.getElementById('browse-filter-playlist').addEventListener('change', event => {
        console.debug('browse: filter-playlist input trigger');
        const playlist = event.target.value;
        if (playlist == 'all') {
            browse.browse(document.getElementById('trans-browse').textContent, {});
        } else {
            browse.browse(document.getElementById('trans-playlist').textContent + playlist, {'playlist': playlist});
        }
    });

    // Button to open browse dialog
    document.getElementById('browse-all').addEventListener('click', () => browse.browseButton());

    // Back button in top left corner of browse window
    document.getElementById('browse-back').addEventListener('click', () => browse.back());
});
