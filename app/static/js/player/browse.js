class Browse {
    /** @type {Array<object>} */
    #history;
    constructor() {
        this.#history = [];

        eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, () => {
            if (dialogs.isOpen('dialog-browse')) {
                this.updateFilter();
            }
        });
    };

    /**
     * @param {string} textContent
     */
    setHeader(textContent) {
        document.getElementById('dialog-browse').getElementsByTagName('h2')[0].textContent = textContent;
    };

    /**
     * @param {HTMLTableElement} table
     */
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

    /**
     * @callback TrackFilter
     * @param {Track} track
     * @returns {boolean}
     */
    /**
     * @param {string} title
     * @param {TrackFilter} filter
     */
    browse(title, filter) {
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

        console.time('update-browse');

        const current = this.#history[this.#history.length - 1];
        this.setHeader(current.title);

        // Playlist filter (or 'all')
        const playlist = document.getElementById('browse-filter-playlist').value;

        let hasFilter = true;
        let filter;
        if (playlist === 'all') {
            if (current.filter === null) {
                // Show all tracks
                filter = () => true;
                hasFilter = false;
            } else {
                // Apply filter to tracks in all playlist
                filter = current.filter;
            }
        } else {
            if (current.filter === null) {
                // Show tracks in specific playlist
                filter = track => track.playlistName === playlist;
            } else {
                // Apply filter to tracks in specific playlists
                filter = track => current.filter(track) && track.playlistName === playlist;
            }
        }

        let content;
        if (hasFilter) {
            const tracks = Object.values(music.tracks).filter(filter);
            content = this.generateTrackList(tracks);
        } else {
            // No selected playlist, or filter. For performance reasons, don't display entire track list.
            content = null;
        }
        this.setContent(content);

        console.timeEnd('update-browse');
    }

    /**
     * @param {string} artistName
     */
    browseArtist(artistName) {
        const title = document.getElementById('trans-artist').textContent + artistName;
        artistName = artistName.toUpperCase();
        this.browse(title, track => track.artists !== null && track.artistsUppercase.indexOf(artistName) !== -1);
    };

    /**
     * @param {string} albumName
     * @param {string} albumArtistName
     */
    browseAlbum(albumName, albumArtistName) {
        const title = document.getElementById('trans-album').textContent + (albumArtistName === null ? '' : albumArtistName + ' - ') + albumName;
        albumName = albumName.toUpperCase();
        if (albumArtistName) {
            albumArtistName = albumArtistName.toUpperCase();
            this.browse(title, track => track.albumUppercase === albumName && track.albumArtistUppercase === albumArtistName);
        } else {
            this.browse(title, track => track.albumUppercase === albumName);
        }
    };

    /**
     * @param {string} tagName
     */
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
        const hcolAddTop = document.createElement('th');
        const hcolAddBottom = document.createElement('th');
        const hcolEdit = document.createElement('th')
        headerRow.replaceChildren(hcolPlaylist, hcolDuration, hcolTitle, hcolAddTop, hcolAddBottom, hcolEdit);



        for (const track of tracks) {
            const colPlaylist = document.createElement('td');
            colPlaylist.textContent = track.playlistName;

            const colDuration = document.createElement('td');
            colDuration.append(durationToString(track.duration));

            const colTitle = document.createElement('td');
            colTitle.replaceChildren(track.displayHtml());

            const colAddTop = document.createElement('td');
            const addTopButton = createIconButton('playlist-plus.svg', ['vflip']);
            colAddTop.replaceChildren(addTopButton);

            const colAddBottom = document.createElement('td');
            const addBottomButton = createIconButton('playlist-plus.svg');
            colAddBottom.replaceChildren(addBottomButton);

            const addButtonFunction = async function(top) {
                for (const button of [addTopButton, addBottomButton]) {
                    replaceIconButton(button, 'loading.svg');
                    button.firstChild.classList.add('spinning');
                    button.disabled = true;
                }
                try {
                    await track.downloadAndAddToQueue(top);
                } catch (ex) {
                    console.error('browse: error adding track to queue', ex)
                }

                for (const button of [addTopButton, addBottomButton]) {
                    replaceIconButton(button, 'playlist-plus.svg')
                    button.firstChild.classList.remove('spinning');
                    button.disabled = false;
                }
            }

            addTopButton.onclick = () => addButtonFunction(true);
            addBottomButton.onclick = () => addButtonFunction(false);

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

    // Button to open browse dialog
    document.getElementById('browse-all').addEventListener('click', () => browse.browseAll());

    // Back button in top left corner of browse window
    document.getElementById('browse-back').addEventListener('click', () => browse.back());
});
