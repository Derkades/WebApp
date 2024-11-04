const SETTING_ELEMENTS = [
    'settings-queue-size',
    'settings-audio-type',
    'settings-volume',
    'settings-queue-removal-behaviour',
    'settings-download-mode',
    'settings-audio-gain',
    'settings-meme-mode',
    'settings-news',
    'settings-theater',
    'settings-visualiser',
    'settings-lyrics',
];

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

function getTrackDownloadParams() {
    let audioType = document.getElementById('settings-audio-type').value;

    if (audioType.startsWith('webm') &&
            getAudioElement().canPlayType("audio/webm;codecs=opus") != "probably" &&
            getAudioElement().canPlayType("video/mp4;codecs=mp4a.40.2") == "probably") {
        alert("WEBM/OPUS audio not supported by your browser, audio quality has been set to MP4/AAC");
        document.getElementById('settings-audio-type').value = "mp4_aac";
        audioType = "mp4_aac";
    }

    const stream = document.getElementById('settings-download-mode').value == 'stream';
    const memeCover = document.getElementById('settings-meme-mode').checked;
    return [audioType, stream, memeCover];
}

document.addEventListener('DOMContentLoaded', () => {
    SETTING_ELEMENTS.forEach(syncInputWithStorage);
    eventBus.publish(MusicEvent.SETTINGS_LOADED);

    document.getElementById('settings-queue-size').addEventListener('input', () => queue.fill());
});
