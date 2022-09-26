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
        const nodes = [];
        for (const track of state.tracks) {
            if (!filterFunc(track)) {
                continue;
            }

            nodes.push(getTrackDisplayHtml(track));
            nodes.push(document.createElement('br'));
        }
        console.log(nodes);
        dialog.setContent(nodes);
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
}
