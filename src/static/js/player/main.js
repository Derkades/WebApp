const state = {
    /** @type {int} */
    maxTrackListSize: 500,
    /** @type {int} */
    maxTrackListSizeSearch: 25,
    /** @type {string} */
    lastChosenPlaylist: null,
    /** @type {Array<string>} */
    playlistOverrides: [],
    /** @type {Object.<string, Playlist>} */
    playlists: null,
    /** @type {Object.<string, Track> | null} */
    tracks: null,
    /** @type {boolean} */
    loadingOverlayHidden: false,
};

document.addEventListener('DOMContentLoaded', () => {
    syncCookiesWithInputs();
    applyTheme();
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

    document.getElementById('button-home').addEventListener('click', () => window.open('/', '_blank'));

    document.getElementById('settings-volume').addEventListener('input', () => onVolumeChange());

    // Queue
    queue.fill();
    document.getElementById('queue-up').addEventListener('click', () => queue.scroll('up'));
    document.getElementById('queue-down').addEventListener('click', () => queue.scroll('down'));

    // Lyrics / album cover switch
    document.getElementById('button-lyrics').addEventListener('click', switchLyrics);
    document.getElementById('button-album').addEventListener('click', switchAlbumCover);
    document.getElementById('button-album').classList.add('hidden');
    document.getElementById('album-covers').addEventListener('click', event => {
        event.preventDefault();
        switchLyrics();
    });
    document.getElementById('lyrics-box').addEventListener('click', event => {
        event.preventDefault();
        switchAlbumCover();
    });

    // Settings overlay
    const downloadSubmit = document.getElementById('youtube-dl-submit');
    if (downloadSubmit !== null) {
        document.getElementById('youtube-dl-submit').addEventListener('click', youTubeDownload);
    } else {
        console.warn('Downloader submit button missing from page, this is normal if you are not an admin user');
    }
    document.getElementById('scan-button').addEventListener('click', () => (async function() {
        const spinner = document.getElementById('scan-spinner');
        const button = document.getElementById('scan-button');
        spinner.classList.remove('hidden');
        button.classList.add('hidden');
        await jsonPost('/scan_music', {});
        await Track.updateLocalTrackList();
        spinner.classList.add('hidden');
        button.classList.remove('hidden');
    })());
    document.getElementById('settings-queue-size').addEventListener('input', () => queue.fill());
    document.getElementById('settings-theme').addEventListener('input', applyTheme);

    // Queue overlay
    document.getElementById('browse-filter-playlist').addEventListener('input', () => browse.updateCurrentView());
    document.getElementById('browse-filter-query').addEventListener('input', () => browse.updateCurrentView());
    document.getElementById('browse-all').addEventListener('click', () => browse.browseAll());
    document.getElementById('browse-back').addEventListener('click', () => browse.back());

    // Never play button
    document.getElementById('button-never-play').addEventListener('click', () => {
        const data = {track: queue.currentTrack.trackPath};
        jsonPost('/add_never_play', data);
        queue.next();
    });

    // Editor
    const editorButton = document.getElementById('button-edit');
    if (editorButton !== null) {
        editorButton.addEventListener('click', () => {
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
        document.getElementById('editor-save').addEventListener('click', () => editor.save());
    } else {
        console.warn('Editor button missing from page, this is normal if you are not an admin user');
    }

    // Delete track button
    const deleteButton = document.getElementById('button-delete-track');
    if (deleteButton !== null) {
        deleteButton.addEventListener('click', () => {
            if (queue.currentTrack === null) {
                return;
            }
            const deleteSpinner = document.getElementById('delete-spinner');
            deleteSpinner.classList.remove('hidden');
            const path = queue.currentTrack.trackPath;
            const oldName = path.split('/').pop();
            const newName = '.trash.' + oldName;
            (async function() {
                await jsonPost('/files_rename', {path: path, new_name: newName});
                await Track.updateLocalTrackList();
                queue.next();
                deleteSpinner.classList.add('hidden');
            })();
        });
    } else {
        console.warn('Editor button missing from page, this is normal if you are not an admin user');
    }

    document.getElementById('button-copy').addEventListener('click', () => {
        const onError = response => {
            if (response.status == 200) {
                response.text().then(text => alert(text));
            } else {
                alert('error');
            }
        }
        jsonPost('/player_copy_track', {track: queue.currentTrack.trackPath}, onError)
    });

    queue.next();
    initTrackList();
    setInterval(refreshCsrfToken, 15*60*1000);
});

function initTrackList() {
    Track.updateLocalTrackList().catch(err => {
        console.warn('track list | error');
        console.warn(err);
        setTimeout(initTrackList, 1000);
    });
}
