function findTrackByPath(path) {
    for (const track of state.tracks) {
        if (track.path === path) {
            return track;
        }
    }
    return null;
}

function initTrackList() {
    console.info('Requesting track list');
    (async function() {
        const response = await fetch('/track_list');
        const json = await response.json();

        state.playlists = json.playlists;
        state.mainPlaylists = [];
        state.guestPlaylists = [];
        for (const dir_name in state.playlists) {
            // TODO sort alphabetically by display name
            const playlist = state.playlists[dir_name];
            if (playlist.guest) {
                state.guestPlaylists.push(playlist);
            } else {
                state.mainPlaylists.push(playlist);
            }
        }

        state.tracks = json.tracks;

        setTimeout(initTrackList, 60_000);
        hideLoadingOverlay();

        // Update HTML depending on state.playlists and state.tracks
        updatePlaylistCheckboxHtml();
        searchTrackList();
        createPlaylistDropdowns();
        updateTagCheckboxes();
    })().catch(err => {
        console.warn('track list | error');
        console.warn(err);
        setTimeout(initTrackList, 1000);
    });
}
