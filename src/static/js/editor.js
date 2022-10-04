const editor = {
    open: (track) => {
        if (track === undefined) {
            track = state.current;
        }
        document.getElementById('editor-title').value = track.title;
        document.getElementById('editor-album').value = track.album;
        document.getElementById('editor-artists').value = track.artists !== null ? track.artists.join('/') : '';
        document.getElementById('editor-album-artist').value = track.album_artist;
        document.getElementById('editor-tags').value = track.tags.join('/');

        document.getElementById('dialog-editor').style.display = 'flex';
    },
    getValue: (id, list = false) => {
        let value = document.getElementById(id).value;
        if (list) {
            const list = value.split('/');
            for (let i = 0; i < list.length; i++) {
                list[i] = list[i].trim();
            }
            return list;
        } else {
            value = value.trim();
            return value === '' ? null : value;
        }
    },
    save: async function() {
        const payload = {
            title: editor.getValue('editor-title'),
            album: editor.getValue('editor-album'),
            artists: editor.getValue('editor-artists', true),
            album_artist: editor.getValue('editor-album-artist'),
            tags: editor.getValue('editor-tags', true),
        }

        const response = await fetch(
            '/update_metadata',
            {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)}
        );
        checkResponseCode(response);

        document.getElementById('dialog-editor').style.display = 'none';
        alert('Saved!');
    },
};
