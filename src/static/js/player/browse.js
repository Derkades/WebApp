class Browse {
    #history;
    constructor() {
        this.#history = [];
    };

    setHeader(textContent) {
        document.getElementById('dialog-browse').getElementsByTagName('h3')[0].textContent = textContent;
    };

    setContent(child) {
        document.getElementById('browse-content').replaceChildren(child);
    };

    open() {
        dialog.open('dialog-browse');
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
        const tracks = this.filterTracks(state.tracks, current.filter);
        this.setContent(this.generateTrackList(tracks));
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
        this.browse(albumText + title, track => track.album === albumName);
    };

    browseTag(tagName) {
        const tagText = document.getElementById('trans-tag').textContent;
        this.browse(tagText + tagName, track => track.tags.indexOf(tagName) !== -1)
    };

    browsePlaylist(playlist) {
        document.getElementById('browse-filter-playlist').value = playlist;
        this.browseAll();
    };

    browseAll() {
        const allText = document.getElementById('trans-all-tracks').textContent;
        this.browse(allText, () => true);
    };

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
            colPlaylist.textContent = track.playlistDisplay;

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
            const editButton = createIconButton('pencil.svg');
            editButton.onclick = () => editor.open(track);
            colEdit.replaceChildren(editButton);

            const dataRow = document.createElement('tr');
            dataRow.replaceChildren(colPlaylist, colDuration, colTitle, colAddTop, colAddBottom, colEdit);
            table.appendChild(dataRow);
        }
        return table;
    };

    getSearchScore(track, playlist, query) {
        if (playlist === 'all' || playlist === track.playlist) {
            const matchProperties = [track.path, track.display, ...track.tags];
            if (track.album !== null) {
                matchProperties.push(track.album);
            }
            if (track.artists !== null) {
                matchProperties.push(track.artists.join(' & '));
            }
            if (track.albumArtist !== null) {
                matchProperties.push(track.albumArtist);
            }

            if (query !== '') {
                let score = 0;
                for (const matchProperty of matchProperties) {
                    let partialScore = matchProperty.length - levenshtein(matchProperty.toLowerCase(), query);
                    // Boost exact matches
                    if (matchProperty.toLowerCase().includes(query)) {
                        partialScore *= 2;
                    }
                    score += partialScore;
                }
                return score;
            } else {
                // No query, same score for all tracks
                return 1;
            }
        }
    };

    filterTracks(tracks, customFilter) {
        // Playlist filter (or 'all')
        const playlist = document.getElementById('browse-filter-playlist').value;
        // Search query text field
        const query = document.getElementById('browse-filter-query').value.trim().toLowerCase();

        let combinedFilter;
        if (playlist === 'all') {
            combinedFilter = customFilter;
        } else {
            combinedFilter = track => customFilter(track) && track.playlistPath == playlist;
        }

        if (query === '') {
            return tracks.filter(combinedFilter).slice(0, state.maxTrackListSize);
        } else {
            // Assign score to all tracks, then sort tracks by score. Finally, get original track object back.
            return tracks
                    .filter(combinedFilter)
                    .map(track => { return {track: track, score: this.getSearchScore(track, playlist, query)}})
                    .sort((a, b) => b.score - a.score)
                    .slice(0, state.maxTrackListSizeSearch)
                    .map(sortedTrack => sortedTrack.track);
        }
    };

};

const browse = new Browse();
