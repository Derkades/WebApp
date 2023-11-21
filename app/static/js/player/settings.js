function syncInputWithStorage(elemId) {
    const elem = document.getElementById(elemId);
    const isCheckbox = elem.matches('input[type="checkbox"]');

    if (elem.dataset.restore === 'false') {
        return;
    }

    // Initialize input form local storage
    const value = window.localStorage.getItem(elemId);
    if (value !== null) {
        if (isCheckbox) {
            elem.checked = value === 'true';
        } else {
            elem.value = value;
        }
    }

    // If input value is updated, change storage accordingly
    elem.addEventListener('input', event => {
        const value = isCheckbox ? event.target.checked : event.target.value;
        window.localStorage.setItem(elemId, value);
    });
}

function syncInputsWithStorage() {
    [
        'settings-queue-size',
        'settings-audio-type',
        'settings-volume',
        'settings-queue-removal-behaviour',
        'settings-download-mode',
        // 'settings-theme',
        'settings-meme-mode',
        // 'settings-language',
    ].forEach(syncInputWithStorage);

    onVolumeChange();
}

document.addEventListener('DOMContentLoaded', () => {
    syncInputsWithStorage();

    document.getElementById('scan-button').addEventListener('click', () => (async function() {
        const spinner = document.getElementById('scan-spinner');
        const button = document.getElementById('scan-button');
        spinner.classList.remove('hidden');
        button.classList.add('hidden');
        await Track.updateLocalTrackList();
        spinner.classList.add('hidden');
        button.classList.remove('hidden');
    })());

    document.getElementById('settings-queue-size').addEventListener('input', () => queue.fill());
});
