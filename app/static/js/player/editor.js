class Editor {
    /** @type {Track} */
    #track;

    constructor() {
        this.#track = null;
    };

    /**
     * Populate input fields and show metadata editor window
     * @param {Track} track
     */
    open(track) {
        if (track == null) {
            throw new Error('Track is null');
        }
        this.#track = track;

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

    setValue(id, value) {
        if (value instanceof Array) {
            value = value.join('; ');
        }
        document.getElementById(id).value = value;
    }

    /**
     * Copy content from track object variables to HTML input fields
     */
    trackToHtml() {
        this.setValue('editor-title', this.#track.title);
        this.setValue('editor-album', this.#track.album);
        this.setValue('editor-artists', this.#track.artists);
        this.setValue('editor-album-artist', this.#track.albumArtist);
        this.setValue('editor-tags', this.#track.tags);
        this.setValue('editor-year', this.#track.year);
    }

    /**
     * Copy content from input fields to track object
     */
    htmlToTrack() {
        this.#track.title = this.getValue('editor-title');
        this.#track.album = this.getValue('editor-album');
        this.#track.artists = this.getValue('editor-artists', true);
        this.#track.albumArtist = this.getValue('editor-album-artist');
        this.#track.tags = this.getValue('editor-tags', true);
        this.#track.year = this.getValue('editor-year');
    }

    /**
     * Save metadata and close metadata editor window
     */
    async save() {
        this.htmlToTrack();

        // Loading text
        document.getElementById('editor-save').classList.add("hidden");
        document.getElementById('editor-writing').classList.remove("hidden");

        // Make request to update metadata
        try {
            this.#track.saveMetadata();
        } catch (e) {
            alert('An error occurred while updating metadata.');
            document.getElementById('editor-writing').classList.add('hidden');
            document.getElementById('editor-save').classList.remove('hidden');
            return;
        }

        // Close dialog, and restore save button
        dialogs.close('dialog-editor');
        document.getElementById('editor-writing').classList.add('hidden');
        document.getElementById('editor-save').classList.remove('hidden');
        this.#track = null;

        // Music player should update all track-related HTML with new metadata
        eventBus.publish(MusicEvent.METADATA_CHANGE);
    };

};

const editor = new Editor();

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('button-edit')) {
        console.warn('edit button not present')
        return;
    }

    // Editor open button
    document.getElementById('button-edit').addEventListener('click', () => {
        if (queue.currentTrack === null) {
            alert('No current track in queue');
            return;
        }
        editor.open(queue.currentTrack.track);
    });

    // Save button
    document.getElementById('editor-save').addEventListener('click', () => editor.save());
});
