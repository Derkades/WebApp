const dialog = {
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
        document.getElementById('dialog-browse').style.display = 'flex';
    },
    browse: (value, filterFunc) => {
        dialog.open();
        dialog.setHeader(value);
        const tracks = [];
        for (const track of state.tracks) {
            if (filterFunc(track)) {
                tracks.push(track);
            }
        }
        dialog.setContent([dialog.generateTrackList(tracks)]);
    },
    browseArtist: artistName => {
        dialog.browse(artistName, track => {
            if (track.artists === null) {
                return false;
            }
            for (const artist of track.artists) {
                if (artist === artistName) {
                    return true;
                }
            }
            return false;
        }
        );
    },
    browseAlbum: albumName => {
        dialog.browse(albumName, track => track.album === albumName);
    },
    generateTrackList: tracks => {
        // TODO two buttons, top of queue bottom of queue
        const table = document.createElement('table');
        table.classList.add('track-list-table');
        const headerRow = document.createElement('tr');
        table.appendChild(headerRow);
        const hcolPlaylist = document.createElement('th');
        const hcolTitle = document.createElement('th');
        const hcolAdd = document.createElement('th');
        headerRow.replaceChildren(hcolPlaylist, hcolTitle, hcolAdd);

        for (const track of tracks) {
            const dataRow = document.createElement('tr');
            const colPlaylist = document.createElement('td');
            colPlaylist.textContent = track.playlist;
            const colTitle = document.createElement('td');
            colTitle.replaceChildren(getTrackDisplayHtml(track));
            const colAdd = document.createElement('td');
            const addButton = document.createElement('button'); // TODO icon button
            addButton.textContent = 'Enqueue'
            addButton.onclick = () => downloadAndAddToQueue(track, true);
            colAdd.replaceChildren(addButton);
            dataRow.replaceChildren(colPlaylist, colTitle, colAdd);
            table.appendChild(dataRow);
        }
        return table;
    }
}
