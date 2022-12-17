const state = {
    maxTrackListSize: 500,
    maxTrackListSizeSearch: 25,
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
    document.getElementById('button-prev').addEventListener('click', () => queue.previous());
    document.getElementById('button-play').addEventListener('click', play);
    document.getElementById('button-pause').addEventListener('click', pause);
    document.getElementById('button-next').addEventListener('click', () => queue.next());
    document.getElementById('settings-volume').addEventListener('input', () => {
        const audioElem = getAudioElement();
        if (audioElem !== null) {
            audioElem.volume = getTransformedVolume();
        }
    });

    // Progress bar seeking
    const onMove = event => {
        seekTo((event.clientX - progressBar.offsetLeft) / progressBar.offsetWidth);
        event.preventDefault(); // Prevent accidental text selection
    };
    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    };
    const progressBar = document.getElementById('outer-progress-bar');
    progressBar.addEventListener('mousedown', event => {
        seekTo((event.clientX - progressBar.offsetLeft) / progressBar.offsetWidth);

        // Keep updating while mouse is moving
        document.addEventListener('mousemove', onMove);

        // Unregister events on mouseup event
        document.addEventListener('mouseup', onUp);

        event.preventDefault(); // Prevent accidental text selection
    });

    // Queue
    queue.fill();
    document.getElementById('queue-up').addEventListener('click', () => queue.scroll('up'));
    document.getElementById('queue-down').addEventListener('click', () => queue.scroll('down'));

    // Lyrics
    document.getElementById('button-lyrics').addEventListener('click', switchLyrics);
    document.getElementById('button-album').addEventListener('click', switchAlbumCover);
    document.getElementById('button-album').classList.add('hidden');

    // Settings overlay
    const downloadSubmit = document.getElementById('youtube-dl-submit');
    if (downloadSubmit !== null) {
        document.getElementById('youtube-dl-submit').addEventListener('click', youTubeDownload);
    } else {
        console.warn('Downloader submit button missing from page, this is normal if you are not an admin user');
    }
    document.getElementById('scan-button').addEventListener('click', () => (async function() {
        const selectedPlaylist = document.getElementById('scan-playlist').value;
        const spinner = document.getElementById('scan-spinner');
        const button = document.getElementById('scan-button');
        spinner.classList.remove('hidden');
        button.disabled = true;
        if (selectedPlaylist !== "") {
            await Track.scanPlaylist(selectedPlaylist);
        } else {
            await Track.scanPlaylist();
        }
        await Track.updateLocalTrackList();
        spinner.classList.add('hidden');
        button.disabled = false;
    })());
    document.getElementById('settings-queue-size').addEventListener('input', () => queue.fill());
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
            if (queue.currentTrack !== null) {
                editor.open(queue.currentTrack);
            }
        });
        document.getElementById('editor-save').addEventListener('click', () => editor.save());
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
    navigator.mediaSession.setActionHandler('previoustrack', () => queue.previous());
    navigator.mediaSession.setActionHandler('nexttrack', () => queue.next());

    // Delete track button
    const deleteButton = document.getElementById('button-delete-track');
    if (deleteButton !== null) {
        deleteButton.addEventListener('click', () => {
            if (queue.currentTrack === null) {
                return;
            }
            const deleteSpinner = document.getElementById('delete-spinner');
            deleteSpinner.classList.remove('hidden');
            const path = queue.currentTrack.path;
            const oldName = path.split('/').pop();
            const newName = '.trash.' + oldName;
            (async function() {
                await jsonPost('/files_rename', {path: path, new_name: newName});
                await Track.scanPlaylist(queue.currentTrack.playlistPath);
                await Track.updateLocalTrackList();
                queue.next();
                deleteSpinner.classList.add('hidden');
            })();
        });
    } else {
        console.warn('Editor button missing from page, this is normal if you are not an admin user');
    }

    lastfm.init();
    queue.next();
    setInterval(updateMediaSession, 500);
    setInterval(updateMediaSessionPosition, 5000);
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
