function findTrackByPath(path) {
    for (const track of state.tracks) {
        if (track.path === path) {
            return track;
        }
    }
    return null;
}

function initTrackList(skip = 0) {
    console.info('requesting track list, from track ' + skip);
    (async function() {
        const response = await fetch('/track_list?skip=' + skip);
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

        if (skip === 0) {
            state.tracks = json.tracks;
        } else {
            for (const track of json.tracks) {
                state.tracks.push(track);
            }
        }

        if (json.partial) {
            setTimeout(() => initTrackList(json.index + 1), 100);
        } else {
            setTimeout(initTrackList, 60_000)
        }

        // Update HTML depending on state.playlists and state.tracks
        updatePlaylistCheckboxHtml();
        searchTrackList();
        updateTagCheckboxes();
    })().catch(err => {
        console.warn('track list | error');
        console.warn(err);
        setTimeout(() => initTrackList(skip), 1000);
    });
}
