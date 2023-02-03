class Browse {
    #history;
    constructor() {
        this.#history = [];
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
        this.open();
        this.setHeader(title);
        this.#history.push({
            title: title,
            filter: filter,
        });
        this.updateCurrentView();
    };

    updateCurrentView() {
        if (this.#history.length === 0) {
            return;
        }

        const current = this.#history[this.#history.length - 1];
        this.setHeader(current.title);

        // Playlist filter (or 'all')
        const playlist = document.getElementById('browse-filter-playlist').value;
        // Search query text field
        const query = document.getElementById('browse-filter-query').value.trim().toLowerCase();

        if (query === '' && playlist === 'all' && current.filter === null) {
            // No search query, selected playlist, or filter. For performance reasons, don't display entire track list.
            this.setContent(null);
            return;
        }

        let filter;
        if (playlist === 'all') {
            if (current.filter === null) {
                // Show all tracks
                filter = () => true;
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

        // Assign score to all tracks, then sort tracks by score. Finally, get original track object back.
        const tracks = Object.values(state.tracks)
                    .filter(filter)
                    .map(track => { return {track: track, score: this.getSearchScore(track, query)}})
                    .sort((a, b) => b.score - a.score)
                    .slice(0, query === '' ? state.maxTrackListSize : state.maxTrackListSizeSearch)
                    .map(sortedTrack => sortedTrack.track);

        const table = this.generateTrackList(tracks);

        this.setContent(table);
    };

    back() {
        if (this.#history.length < 2) {
            return;
        }
        this.#history.pop();
        this.updateCurrentView();
    };

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

    getSearchScore(track, query) {
        if (query === '') {
            // No query, same score for all tracks
            return 1;
        }

        const matchProperties = [track.display];
        if (track.album !== null) {
            matchProperties.push(track.album);
        }
        if (track.artists !== null) {
            for (const artist of track.artists) {
                matchProperties.push(artist);
            }
        }

        let score = 0;

        for (const matchProperty of matchProperties) {
            if (matchProperty.toLowerCase().includes(query)) {
                score += 2;
            }
        }

        const parts = query.split(' ');
        for (const part of parts) {
            for (const matchProperty of matchProperties) {
                if (matchProperty.toLowerCase().includes(part)) {
                    score += 2 / parts.length;
                } else {
                    score += 1 / (levenshtein(matchProperty.toLowerCase(), query) * parts.length);
                }
            }
        }

        return score;
    };
};

const browse = new Browse();
