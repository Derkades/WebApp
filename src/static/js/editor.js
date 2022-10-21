class Editor {
    #currentlyEditingPath;

    constructor() {
        this.#currentlyEditingPath = null;
    };

    open(track) {
        if (track == null) {
            throw new Error('Track is null');
        }
        this.#currentlyEditingPath = track.path;
        document.getElementById('editor-title').value = track.title;
        document.getElementById('editor-album').value = track.album;
        document.getElementById('editor-artists').value = track.artists !== null ? track.artists.join(';') : '';
        document.getElementById('editor-album-artist').value = track.albumArtist;
        document.getElementById('editor-tags').value = track.tags.join(';');

        dialog.open('dialog-editor');
    };

    getValue(id, list = false) {
        let value = document.getElementById(id).value;
        if (list) {
            const list = value.split(';');
            for (let i = 0; i < list.length; i++) {
                list[i] = list[i].trim();
            }
            return list
        } else {
            value = value.trim();
            return value === '' ? null : value;
        }
    };

    async save() {
        // POST body for request
        const payload = {
            path: this.#currentlyEditingPath,
                metadata: {
                title: this.getValue('editor-title'),
                album: this.getValue('editor-album'),
                artists: this.getValue('editor-artists', true),
                album_artist: this.getValue('editor-album-artist'),
                tags: this.getValue('editor-tags', true),
            }
        }

        this.#currentlyEditingPath = null;

        // Loading text
        document.getElementById('editor-save').classList.add("hidden");
        document.getElementById('editor-writing').classList.remove("hidden");

        // Make request to update metadata
        jsonPost('/update_metadata', payload);

        // Different loading text
        document.getElementById('editor-writing').classList.add('hidden');
        document.getElementById('editor-reloading').classList.remove('hidden');

        // Need to update local track list now, so metadata editor reflects changes
        await Track.updateLocalTrackList();

        // Close dialog, and restore save button
        dialog.close('dialog-editor');
        document.getElementById('editor-reloading').classList.add('hidden');
        document.getElementById('editor-save').classList.remove('hidden');
    };

};

const editor = new Editor();
