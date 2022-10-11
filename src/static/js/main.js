const state = {
    queue: [],
    current: null,
    history: [],
    queueBusy: false,
    historySize: 20,
    maxTrackListSize: 250,
    lastChosenPlaylist: null,
    playlistOverrides: [],
    playlists: null,
    mainPlaylists: [],
    guestPlaylists: [],
    tracks: null,
    loadingOverlayHidden: false,
};

document.addEventListener("DOMContentLoaded", () => {
    syncCookiesWithInputs();
    applyTheme();
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

    // Playback controls
    document.getElementById('button-skip-previous').addEventListener('click', previous);
    document.getElementById('button-rewind-15').addEventListener('click', () => seek(-15));
    document.getElementById('button-play').addEventListener('click', play);
    document.getElementById('button-pause').addEventListener('click', pause);
    document.getElementById('button-fast-forward-15').addEventListener('click', () => seek(15));
    document.getElementById('button-skip-next').addEventListener('click', next);
    document.getElementById('settings-volume').addEventListener('input', event => {
        const audioElem = getAudioElement();
        if (audioElem !== null) {
            audioElem.volume = getTransformedVolume();
        }
    });

    // Queue
    updateQueue();

    // Lyrics
    document.getElementById('button-microphone').addEventListener('click', switchLyrics);
    document.getElementById('button-album').addEventListener('click', switchAlbumCover);
    document.getElementById('button-album').style.display = 'none';

    // Settings overlay
    const downloadSubmit = document.getElementById('youtube-dl-submit');
    if (downloadSubmit !== null) {
        document.getElementById('youtube-dl-submit').addEventListener('click', youTubeDownload);
    } else {
        console.warn('Downloader submit button missing from page, this is normal if you are not an admin user');
    }
    document.getElementById('settings-queue-size').addEventListener('input', updateQueue);
    document.getElementById('settings-theme').addEventListener('input', applyTheme);

    // Queue overlay
    document.getElementById('browse-filter-playlist').addEventListener('input', () => browse.updateCurrentView());
    document.getElementById('browse-filter-query').addEventListener('input', () => browse.updateCurrentView());
    document.getElementById('browse-all').addEventListener('click', () => browse.browseAll());
    document.getElementById('browse-back').addEventListener('click', () => browse.back());

    // Editor
    const editorButton = document.getElementById('button-edit');
    if (editorButton !== null) {
        editorButton.addEventListener('click', () => {
            if (state.current !== null) {
                editor.open(state.current);
            }
        });
        document.getElementById('editor-save').addEventListener('click', editor.save);
    } else {
        console.warn('Editor button missing from page, this is normal if you are not an admin user');
    }

    // Dialogs
    dialog.registerEvents();

    // Hotkeys
    document.addEventListener('keydown', event => handleKey(event.key));

    navigator.mediaSession.setActionHandler('play', play);
    navigator.mediaSession.setActionHandler('pause', pause);
    navigator.mediaSession.setActionHandler('seekto', callback => {
        const audio = getAudioElement();
        if (audio != null) {
            audio.currentTime = callback.seekTime;
        }
    });
    navigator.mediaSession.setActionHandler('previoustrack', previous);
    navigator.mediaSession.setActionHandler('nexttrack', next);

    next();
    setInterval(updateMediaSession, 500);
    setInterval(updateMediaSessionPosition, 5000);
    initTrackList();
});

function initTrackList() {
    Track.updateLocalTrackList().catch(err => {
        console.warn('track list | error');
        console.warn(err);
        setTimeout(initTrackList, 1000);
    });
}
