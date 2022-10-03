const browse = {
    setHeader: textContent => {
        const outerDiv = document.getElementById('dialog-browse');
        const innerDiv = outerDiv.children[0];
        const headerDiv = innerDiv.children[0];
        const header = headerDiv.children[0];
        header.textContent = textContent;
    },
    setContent: children => {
        document.getElementById('browse-content').replaceChildren(...children);
    },
    open: () => {
        for (const dialog of document.getElementsByClassName('dialog-overlay')) {
            dialog.style.display = 'none';
        }
        document.getElementById('dialog-browse').style.display = 'flex';
    },
    browse: (title, filterFunc) => {
        browse.open();
        browse.setHeader(title);
        const tracks = [];
        for (const track of state.tracks) {
            if (filterFunc(track)) {
                tracks.push(track);
            }
        }
        browse.setContent([browse.generateTrackList(tracks)]);
    },
    browseArtist: artistName => {
        browse.browse(artistName, track => track.artists !== null && track.artists.indexOf(artistName) !== -1);
    },
    browseAlbum: (albumName, albumArtistName) => {
        const title = albumArtistName === null ? albumName : albumArtistName + ' - ' + albumName;
        browse.browse(title, track => track.album === albumName);
    },
    browseTag: (tagName) => {
        browse.browse(tagName, track => track.tags.indexOf(tagName) !== -1)
    },
    generateTrackList: tracks => {
        // TODO two buttons, top of queue bottom of queue
        const table = document.createElement('table');
        table.classList.add('track-list-table');
        const headerRow = document.createElement('tr');
        table.appendChild(headerRow);
        const hcolPlaylist = document.createElement('th');
        const hcolTitle = document.createElement('th');
        const hcolAddTop = document.createElement('th');
        const hcolAddBottom = document.createElement('th');
        headerRow.replaceChildren(hcolPlaylist, hcolTitle, hcolAddTop, hcolAddBottom);

        let i = 0;
        for (const track of tracks) {
            const colPlaylist = document.createElement('td');
            colPlaylist.textContent = track.playlist;

            const colTitle = document.createElement('td');
            colTitle.replaceChildren(getTrackDisplayHtml(track));

            const colAddTop = document.createElement('td');
            const addTopButton = createIconButton('playlist-plus-top.svg');
            addTopButton.onclick = () => downloadAndAddToQueue(track, true);
            colAddTop.replaceChildren(addTopButton);

            const colAddBottom = document.createElement('td');
            const addButton = createIconButton('playlist-plus.svg');
            colAddBottom.onclick = () => downloadAndAddToQueue(track);
            colAddBottom.replaceChildren(addButton);

            const dataRow = document.createElement('tr');
            dataRow.replaceChildren(colPlaylist, colTitle, colAddTop, colAddBottom);
            table.appendChild(dataRow);
            if (i++ > state.maxTrackListSize) {
                break;
            }

        }
        return table;
    }
}
