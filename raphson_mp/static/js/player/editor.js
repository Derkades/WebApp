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
        this.trackToHtml();

        // Make editor dialog window visisble, and bring it to the top
        dialogs.open('dialog-editor');
    };

    /**
     * @param {string} id
     * @param {boolean} list If enabled, the value is split to a list by the semicolon character
     * @returns Value of HTML input with the given id.
     */
    #getValue(id, isList = false) {
        let value = document.getElementById(id).value;
        if (isList) {
            const list = [];
            for (const item of value.split(';')) {
                const trimmed = item.trim();
                if (trimmed) {
                    list.push(trimmed);
                }
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
        this.setValue('editor-path', this.#track.path);
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
        this.#track.title = this.#getValue('editor-title');
        this.#track.album = this.#getValue('editor-album');
        this.#track.artists = this.#getValue('editor-artists', true);
        this.#track.albumArtist = this.#getValue('editor-album-artist');
        this.#track.tags = this.#getValue('editor-tags', true);
        this.#track.year = this.#getValue('editor-year');
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
            await this.#track.saveMetadata();
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

        // Music player should update all track-related HTML with new metadata. This event must be
        // fired after the editor dialog is closed, so other dialogs can check whether they are open.
        eventBus.publish(MusicEvent.METADATA_CHANGE, this.#track);

        this.#track = null;
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
