const state = {
    queue: [],
    current: null,
    history: [],
    queueBusy: false,
    historySize: 10,
    maxTrackListSize: 500,
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
    document.getElementById('youtube-dl-submit').addEventListener('click', youTubeDownload);
    document.getElementById('settings-queue-size').addEventListener('input', () => updateQueue());

    // Queue overlay
    document.getElementById('track-list-playlist').addEventListener('input', searchTrackList);
    document.getElementById('track-list-query').addEventListener('input', searchTrackList);

    // Dialog open buttons
    for (const elem of document.getElementsByClassName('dialog-overlay')) {
        const openButton = document.getElementById('open-' + elem.id);
        if (openButton === null) {
            console.warn('Dialog ' + elem.id + ' has no open button');
            continue;
        }
        openButton.addEventListener('click', () => elem.style.display = 'flex');
    };

    // Dialog close buttons
    for (const elem of document.getElementsByClassName('dialog-close-button')) {
        elem.addEventListener('click', () => {
            for (const elem of document.getElementsByClassName('dialog-overlay')) {
                elem.style.display = 'none';
            }
        });
    }

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
    searchTrackList();
});
