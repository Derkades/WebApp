document.addEventListener('DOMContentLoaded', () => {
    /** @type {HTMLButtonElement} */
    const addButton = document.getElementById('online-add');
    /** @type {HTMLInputElement} */
    const urlInput = document.getElementById('online-url');

    if (addButton == null) {
        console.debug('online: add button is missing, this is expected in offline mode');
        return;
    }

    addButton.addEventListener('click', async () => {
        dialogs.close('dialog-online');
        const track = await music.downloadTrackFromWeb(urlInput.value);
        queue.add(track, true);
    })
});
