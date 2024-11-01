/**
 * @returns {Array<string>} list of playlist names
 */
function getActivePlaylists() {
    const active = [];

    for (const checkbox of document.getElementById('playlist-checkboxes').getElementsByTagName('input')) {
        if (checkbox.checked) {
            active.push(checkbox.dataset.playlist);
        }
    }

    return active;
}

/**
 * @param {string} currentPlaylist current playlist name
 * @returns {string} next playlist name
 */
function getNextPlaylist(currentPlaylist) {
    const active = getActivePlaylists();

    let playlist;

    if (active.length === 0) {
        // No one is selected
        return null;
    } else if (currentPlaylist === null) {
        // No playlist chosen yet, choose random playlist
        playlist = choice(active);
    } else {
        const currentIndex = active.indexOf(currentPlaylist);
        if (currentIndex === -1) {
            // Current playlist is no longer active, we don't know the logical next playlist
            // Choose random playlist
            playlist = choice(active);
        } else {
            // Choose next playlist in list, wrapping around if at the end
            playlist = active[(currentIndex + 1) % active.length];
        }
    }

    return playlist;
}



/**
 * @returns {void}
 */
async function updatePlaylistCheckboxHtml() {
    console.debug('playlist: update playlist checkboxes');
    const parent = document.getElementById('playlist-checkboxes');
    parent.replaceChildren(await music.getPlaylistCheckboxes());
    for (const input of parent.getElementsByTagName('input')) {
        input.oninput = savePlaylistState;
    }
    loadPlaylistState();
}

/**
 * @param {Array<Playlist>} playlists
 * @returns {void}
 */
function updatePlaylistDropdowns(playlists) {
    console.debug('playlist: updating dropdowns');

    for (const select of document.getElementsByClassName('playlist-select')) {
        const previouslySelectedValue = select.value;

        // Remove all children except the ones that should be kept
        const keptChildren = []
        for (const child of select.children) {
            if (child.dataset.keep === 'true') {
                keptChildren.push(child);
                continue;
            }
        }
        select.replaceChildren(...keptChildren);

        const primaryPlaylist = document.getElementById('primary-playlist').textContent;
        const onlyWritable = select.classList.contains('playlist-select-writable');

        for (const playlist of playlists) {
            const option = document.createElement('option');
            option.value = playlist.name;
            option.textContent = playlist.name;
            option.disabled = onlyWritable && !playlist.write;
            select.appendChild(option);
        }

        // After all options have been replaced, the previously selected option should be restored
        if (previouslySelectedValue == "") {
            select.value = primaryPlaylist;
        } else {
            select.value = previouslySelectedValue;
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const playlists = await music.playlists();
    updatePlaylistCheckboxHtml();
    updatePlaylistDropdowns(playlists);
});

/**
 * Update checked state of playlist checkboxes from local storage
 * @returns {void}
 */
function loadPlaylistState() {
    const playlistsString = localStorage.getItem('playlists');
    if (!playlistsString) {
        console.info('playlist: no state saved');
        return;
    }
    /** @type {Array<string>} */
    const savedPlaylists = JSON.parse(playlistsString);
    console.debug('playlist: restoring state', savedPlaylists);
    const checkboxes = document.getElementById('playlist-checkboxes').getElementsByTagName('input');
    for (const checkbox of checkboxes) {
        checkbox.checked = savedPlaylists.indexOf(checkbox.dataset.playlist) != -1;
    }
}

/**
 * Save state of playlist checkboxes to local storage
 * @returns {void}
 */
function savePlaylistState() {
    const checkboxes = document.getElementById('playlist-checkboxes').getElementsByTagName('input');
    const checkedPlaylists = [];
    for (const checkbox of checkboxes) {
        if (checkbox.checked) {
            checkedPlaylists.push(checkbox.dataset.playlist);
        }
    }
    console.debug('playlist: saving checkbox state', checkedPlaylists);
    localStorage.setItem('playlists', JSON.stringify(checkedPlaylists));
}
