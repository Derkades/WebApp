const editor = {
    currentlyEditingPath: null,
    open: (track) => {
        if (track == null) {
            throw new Error('Track is null');
        }
        editor.currentlyEditingPath = track.path;
        document.getElementById('editor-title').value = track.title;
        document.getElementById('editor-album').value = track.album;
        document.getElementById('editor-artists').value = track.artists !== null ? track.artists.join('/') : '';
        document.getElementById('editor-album-artist').value = track.albumArtist;
        document.getElementById('editor-tags').value = track.tags.join('/');

        dialog.open('dialog-editor');
    },
    getValue: (id, list = false) => {
        let value = document.getElementById(id).value;
        if (list) {
            const list = value.split('/');
            for (let i = 0; i < list.length; i++) {
                list[i] = list[i].trim();
            }
            return list
        } else {
            value = value.trim();
            return value === '' ? null : value;
        }
    },
    save: async function() {
        // POST body for request
        const payload = {
            path: editor.currentlyEditingPath,
                metadata: {
                title: editor.getValue('editor-title'),
                album: editor.getValue('editor-album'),
                artists: editor.getValue('editor-artists', true),
                album_artist: editor.getValue('editor-album-artist'),
                tags: editor.getValue('editor-tags', true),
            }
        }

        editor.currentlyEditingPath = null;

        // Loading text
        document.getElementById('editor-save').classList.add("hidden");
        document.getElementById('editor-writing').classList.remove("hidden");

        // Make request to update metadata
        const response = await fetch(
            '/update_metadata',
            {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)}
        );
        checkResponseCode(response);

        // Different loading text
        document.getElementById('editor-writing').classList.add('hidden');
        document.getElementById('editor-reloading').classList.remove('hidden');

        // Need to update local track list now, so metadata editor reflects changes
        await Track.updateLocalTrackList();

        // Close dialog, and restore save button
        dialog.close('dialog-editor');
        document.getElementById('editor-reloading').classList.add('hidden');
        document.getElementById('editor-save').classList.remove('hidden');
    },
};
