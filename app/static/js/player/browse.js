class Browse {
    /** @type {Array<object>} */
    #history;
    constructor() {
        this.#history = [];

        eventBus.subscribe(MusicEvent.METADATA_CHANGE, () => {
            if (dialogs.isOpen('dialog-browse')) {
                this.updateContent();
            }
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
        this.updateContent();
        this.open();
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

        const current = this.#history[this.#history.length - 1];
        this.setHeader(current.title);

        if (Object.keys(current.filter).length > 0) {
            const tracks = await music.filteredTracks(current.filter);
            const table = this.generateTrackList(tracks);
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
        const title = document.getElementById('trans-artist').textContent + artistName;
        this.browse(title, {'artist': artistName});
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
        const tagText = document.getElementById('trans-tag').textContent;
        this.browse(tagText + tagName, {'tag': tagName})
    };

    /**
     * @param {string} playlistName
     */
    browsePlaylist(playlistName) {
        document.getElementById('browse-filter-playlist').value = playlistName;
        // this triggers an event which calls setPlaylistFilter()
        // const allText = document.getElementById('trans-all-tracks').textContent;
        // this.browse(allText, {'playlist': playlistName});
    };

    browseAll() {
        const allText = document.getElementById('trans-all-tracks').textContent;
        this.browse(allText, {});
    };

    setPlaylistFilter(playlist) {
        if (this.#history.current) {
            this.#history.current.playlist = playlist;
        } else {
            this.browse(document.getElementById('trans-all-tracks').textContent, {'playlist': playlist})
        }
    }

    /**
     * also used by search.js
     * @param {Array<Track>} tracks
     * @returns {HTMLTableElement}
     */
    generateTrackList(tracks) {
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

        const addButton = createIconButton('playlist-plus.svg');
        const editButton = createIconButton('pencil.svg');

        for (const track of tracks) {
            const colPlaylist = document.createElement('td');
            colPlaylist.textContent = track.playlistName;

            const colDuration = document.createElement('td');
            colDuration.textContent = durationToString(track.duration);

            const colTitle = document.createElement('td');
            colTitle.appendChild(track.displayHtml());

            const addButton2 = addButton.cloneNode(true);
            addButton2.addEventListener('click', async function() {
                replaceIconButton(addButton2, 'loading.svg');
                addButton2.firstChild.classList.add('spinning');
                addButton2.disabled = true;

                try {
                    const downloadedTrack = await track.download(...getTrackDownloadParams());
                    queue.add(downloadedTrack, true);
                } catch (ex) {
                    console.error('browse: error adding track to queue', ex)
                }

                replaceIconButton(addButton2, 'playlist-plus.svg')
                addButton2.firstChild.classList.remove('spinning');
                addButton2.disabled = false;
            });
            const colAdd = document.createElement('td');
            colAdd.appendChild(addButton2);

            const colEdit = document.createElement('td');

            if (music.playlist(track.playlistName).write) {
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
        if (event.target.value == 'all') {
            browse.setPlaylistFilter(undefined);
        } else {
            browse.setPlaylistFilter(event.target.value);
        }
        browse.updateContent()
    });

    // Button to open browse dialog
    document.getElementById('browse-all').addEventListener('click', () => browse.browseAll());

    // Back button in top left corner of browse window
    document.getElementById('browse-back').addEventListener('click', () => browse.back());
});
