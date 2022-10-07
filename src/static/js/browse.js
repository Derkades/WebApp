const browse = {
    history: [],
    setHeader: textContent => {
        document.getElementById('dialog-browse').getElementsByTagName('h3')[0].textContent = textContent;
    },
    setContent: child => {
        document.getElementById('browse-content').replaceChildren(child);
    },
    open: () => {
        dialog.open('dialog-browse');
    },
    browse: (title, filter) => {
        browse.open();
        browse.setHeader(title);
        browse.history.push({
            title: title,
            filter: filter,
        });
        browse.updateCurrentView();
    },
    updateCurrentView: () => {
        if (browse.history.length === 0) {
            return;
        }
        const current = browse.history[browse.history.length - 1];
        browse.setHeader(current.title);
        const tracks = browse.filterTracks(state.tracks, current.filter);
        browse.setContent(browse.generateTrackList(tracks));
    },
    back: () => {
        if (browse.history.length < 2) {
            return;
        }
        browse.history.pop();
        browse.updateCurrentView();
    },
    browseArtist: artistName => {
        browse.browse('Artist: ' + artistName, track => track.artists !== null && track.artists.indexOf(artistName) !== -1);
    },
    browseAlbum: (albumName, albumArtistName) => {
        const title = albumArtistName === null ? albumName : albumArtistName + ' - ' + albumName;
        browse.browse('Album: ' + title, track => track.album === albumName);
    },
    browseTag: (tagName) => {
        browse.browse('Tag: ' + tagName, track => track.tags.indexOf(tagName) !== -1)
    },
    browsePlaylist: playlist => {
        document.getElementById('browse-filter-playlist').value = playlist;
        browse.browseAll();
    },
    browseAll: () => {
        // TODO translation
        browse.browse('All tracks', () => true);
    },
    generateTrackList: tracks => {
        const table = document.createElement('table');
        table.classList.add('track-list-table');
        const headerRow = document.createElement('tr');
        table.appendChild(headerRow);
        const hcolPlaylist = document.createElement('th');
        const hcolTitle = document.createElement('th');
        const hcolAddTop = document.createElement('th');
        const hcolAddBottom = document.createElement('th');
        const hcolEdit = document.createElement('th')
        headerRow.replaceChildren(hcolPlaylist, hcolTitle, hcolAddTop, hcolAddBottom, hcolEdit);

        let i = 0;
        for (const track of tracks) {
            const colPlaylist = document.createElement('td');
            colPlaylist.textContent = track.playlist;

            const colTitle = document.createElement('td');
            colTitle.replaceChildren(getTrackDisplayHtml(track));

            const colAddTop = document.createElement('td');
            const addTopButton = createIconButton('playlist-plus.svg', ['vflip']);
            addTopButton.onclick = () => downloadAndAddToQueue(track, true);
            colAddTop.replaceChildren(addTopButton);

            const colAddBottom = document.createElement('td');
            const addButton = createIconButton('playlist-plus.svg');
            addButton.onclick = () => downloadAndAddToQueue(track);
            colAddBottom.replaceChildren(addButton);

            const colEdit = document.createElement('td');
            const editButton = createIconButton('pencil.svg');
            editButton.onclick = () => editor.open(track);
            colEdit.replaceChildren(editButton);

            const dataRow = document.createElement('tr');
            dataRow.replaceChildren(colPlaylist, colTitle, colAddTop, colAddBottom, colEdit);
            table.appendChild(dataRow);
            if (i++ > state.maxTrackListSize) {
                break;
            }

        }
        return table;
    },
    getSearchScore: (track, playlist, query) => {
        if (playlist === 'everyone' || playlist === track.playlist) {
            const matchProperties = [track.path, track.display, ...track.tags];
            if (track.album !== null) {
                matchProperties.push(track.album);
            }
            if (track.artists !== null) {
                matchProperties.push(track.artists.join(' & '));
            }
            if (track.album_artist !== null) {
                matchProperties.push(track.album_artist);
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
    },
    filterTracks: (tracks, customFilter) => {
        // Playlist filter (or 'everyone')
        const playlist = document.getElementById('browse-filter-playlist').value;
        // Search query text field
        const query = document.getElementById('browse-filter-query').value.trim().toLowerCase();

        // Assign score to all tracks, then sort tracks by score. Finally, get original track object back.
        return tracks
                .filter(customFilter)
                .filter(track => playlist === 'everyone' || track.playlist === playlist)
                .map(track => { return {track: track, score: browse.getSearchScore(track, playlist, query)}})
                .sort((a, b) => b.score - a.score)
                .map(sortedTrack => sortedTrack.track);
    }
}
