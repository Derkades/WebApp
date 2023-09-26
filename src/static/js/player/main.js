const state = {
    /** @type {int} */
    maxTrackListSize: 500,
    /** @type {int} */
    maxTrackListSizeSearch: 25,
    /** @type {int} */
    maxHistorySize: 3,
    /** @type {string} */
    lastChosenPlaylist: null,
    /** @type {Array<string>} */
    playlistOverrides: [],
    /** @type {string | null} */
    trackListLastModified: null,
    /** @type {Object.<string, Playlist>} */
    playlists: null,
    /** @type {Object.<string, Track> | null} */
    tracks: null,
    /** @type {boolean} */
    loadingOverlayHidden: false,
};

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('button-home').addEventListener('click', () => window.open('/', '_blank'));

    // Queue
    queue.fill();
});

// Hide loading overlay when track list has finished loading
eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, () => {
    document.getElementById('loading-overlay').classList.add('overlay-hidden');
});
