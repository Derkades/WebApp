class Editor {
    #currentlyEditingPath;

    constructor() {
        this.#currentlyEditingPath = null;
    };

    /**
     * Populate input fields and show metadata editor window
     * @param {Track} track
     */
    open(track) {
        if (track == null) {
            throw new Error('Track is null');
        }
        this.#currentlyEditingPath = track.path;

        // Set content of HTML input fields
        document.getElementById('editor-html-title').textContent = track.path;
        document.getElementById('editor-title').value = track.title;
        document.getElementById('editor-album').value = track.album;
        document.getElementById('editor-artists').value = track.artists !== null ? track.artists.join('; ') : '';
        document.getElementById('editor-album-artist').value = track.albumArtist;
        document.getElementById('editor-tags').value = track.tags.join('; ');
        document.getElementById('editor-year').value = track.year;

        // Make editor dialog window visisble, and bring it to the top
        dialogs.open('dialog-editor');
    };

    /**
     * @param {string} id
     * @param {boolean} list If enabled, the value is split to a list by the semicolon character
     * @returns Value of HTML input with the given id.
     */
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

    /**
     * Save metadata and close metadata editor window
     */
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
                year: this.getValue('editor-year'),
            },
        };

        // Loading text
        document.getElementById('editor-save').classList.add("hidden");
        document.getElementById('editor-writing').classList.remove("hidden");

        // Make request to update metadata
        try {
            await jsonPost('/update_metadata', payload);
        } catch (e) {
            alert('An error occurred while updating metadata.');
            document.getElementById('editor-writing').classList.add('hidden');
            document.getElementById('editor-save').classList.remove('hidden');
            this.#currentlyEditingPath = null;
            return;
        }

        // Different loading text
        document.getElementById('editor-writing').classList.add('hidden');
        document.getElementById('editor-reloading').classList.remove('hidden');

        // Need to update local track list now, so metadata editor reflects changes
        await Track.updateLocalTrackList();

        // Close dialog, and restore save button
        dialogs.close('dialog-editor');
        document.getElementById('editor-reloading').classList.add('hidden');
        document.getElementById('editor-save').classList.remove('hidden');
        this.#currentlyEditingPath = null;
    };

};

const editor = new Editor();

document.addEventListener('DOMContentLoaded', () => {
    // Editor open button
    document.getElementById('button-edit').addEventListener('click', () => {
        if (queue.currentTrack === null) {
            alert('No current track in queue');
            return;
        }
        const track = queue.currentTrack.track();
        if (track === null) {
            alert('Missing track info, has the track been deleted?');
            return;
        }
        editor.open(track);
    });

    // Save button
    document.getElementById('editor-save').addEventListener('click', () => editor.save());
});
