/**
 * @returns {Array<string>} list of playlist names
 */
function getActivePlaylists() {
    const active = [];

    for (const checkbox of document.getElementsByClassName('playlist-checkbox')) {
        const musicDirName = checkbox.id.substring(9); // remove 'checkbox-'
        if (checkbox.checked) {
            active.push(musicDirName);
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
 * @param {Playlist} playlist Playlist
 * @param {number} index Hotkey number, set to >=10 to not assign a hotkey
 * @param {boolean} defaultChecked Whether checkbox should be checked
 * @returns {HTMLSpanElement}
 */
function createPlaylistCheckbox(playlist, index, defaultChecked) {
    const input = document.createElement("input");
    input.type = 'checkbox';
    input.classList.add('playlist-checkbox');
    input.id = 'checkbox-' + playlist.name;
    input.checked = defaultChecked;
    input.oninput = savePlaylistState;

    const sup = document.createElement('sup');
    if (index < 10) { // Assume number keys higher than 9 don't exist
        sup.textContent = index;
    }

    const trackCount = document.createElement('span');
    trackCount.classList.add('secondary');
    trackCount.textContent = ' ' + playlist.trackCount;

    const label = document.createElement("label");
    label.htmlFor = "checkbox-" + playlist.name;
    label.textContent = playlist.name;
    label.replaceChildren(playlist.name, sup, trackCount);

    const span = document.createElement("span");
    span.classList.add("checkbox-with-label");
    span.replaceChildren(input, label);

    return span;
}

/**
 * @param {Array<Playlist>} playlists
 * @returns {void}
 */
function updatePlaylistCheckboxHtml(playlists) {
    console.debug('playlist: update playlist checkboxes');

    let index = 1;
    const mainDiv = document.createElement('div');
    const otherDiv = document.createElement('div');
    otherDiv.classList.add('other-checkboxes');

    for (const playlist of playlists) {
        if (playlist.favorite) {
            mainDiv.appendChild(createPlaylistCheckbox(playlist, index++, true));
        } else {
            otherDiv.appendChild(createPlaylistCheckbox(playlist, 10, false));
        }
    }

    const parent = document.getElementById('playlist-checkboxes');
    parent.replaceChildren(mainDiv, otherDiv);

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
    updatePlaylistCheckboxHtml(playlists)
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
    const savedPlaylists = JSON.parse(playlistsString);
    console.debug('playlist: restoring state', savedPlaylists);
    const checkboxes = document.getElementById('playlist-checkboxes').querySelectorAll('.playlist-checkbox');
    for (const checkbox of checkboxes) {
        checkbox.checked = 0;
    }
    for (const playlist of savedPlaylists) {
        document.getElementById('checkbox-' + playlist).checked = 1;
    }
}

/**
 * Save state of playlist checkboxes to local storage
 * @returns {void}
 */
function savePlaylistState() {
    const checkboxes = document.getElementById('playlist-checkboxes').querySelectorAll('.playlist-checkbox');
    const checkedPlaylists = [];
    for (const checkbox of checkboxes) {
        if (checkbox.checked) {
            checkedPlaylists.push(checkbox.id.substring('checkbox-'.length));
        }
    }
    console.debug('playlist: saving checkbox state', checkedPlaylists);
    localStorage.setItem('playlists', JSON.stringify(checkedPlaylists));
}
