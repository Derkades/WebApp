class Playlist {
    /** @type {string} */
    name;
    /** @type {number} */
    trackCount;
    /** @type {boolean} */
    favorite;
    /** @type {boolean} */
    write;

    /**
     * @param {Object.<string, string|boolean|number} objectFromApi
     */
    constructor(objectFromApi) {
        this.name = objectFromApi.name;
        this.trackCount = objectFromApi.track_count;
        this.favorite = objectFromApi.favorite;
        this.write = objectFromApi.write;
    }
}

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
 *
 * @param {Playlist} playlist
 * @param {number} index
 * @returns {HTMLSpanElement}
 */
function createPlaylistCheckbox(playlist, index, defaultChecked) {
    const span = document.createElement("span");
    span.classList.add("checkbox-with-label");

    const input = document.createElement("input");
    input.type = 'checkbox';
    input.classList.add('playlist-checkbox');
    input.id = 'checkbox-' + playlist.name;
    input.checked = defaultChecked;
    input.oninput = savePlaylistState;

    const label = document.createElement("label");
    label.htmlFor = "checkbox-" + playlist.name;
    label.textContent = playlist.name;
    const sup = document.createElement('sup');
    if (index < 10) { // Assume number keys higher than 9 don't exist
        sup.textContent = index;
    }

    const trackCount = document.createElement('span');
    trackCount.classList.add('secondary');
    trackCount.textContent = ` (${playlist.trackCount})`;

    label.replaceChildren(
        playlist.name,
        sup,
        trackCount,
    );

    span.appendChild(input);
    span.appendChild(label);

    return span;
}

function updatePlaylistCheckboxHtml() {
    let index = 1;
    const mainDiv = document.createElement('div');
    const otherDiv = document.createElement('div');
    otherDiv.classList.add('other-checkboxes');

    for (const playlist of Object.values(state.playlists)) {
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
eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, updatePlaylistCheckboxHtml);

function createPlaylistDropdowns() {
    for (const select of document.getElementsByClassName('playlist-select')) {
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

        for (const playlist of Object.values(state.playlists)) {
            const option = document.createElement('option');
            option.value = playlist.name;
            option.textContent = playlist.name;
            option.disabled = onlyWritable && !playlist.write;
            option.selected = keptChildren.length == 0 && playlist.name == primaryPlaylist;
            select.appendChild(option);
        }
    }
}
eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, createPlaylistDropdowns);

function loadPlaylistState() {
    const playlistsString = localStorage.getItem('playlists');
    if (!playlistsString) {
        console.info('No playlists state saved');
        return;
    }
    const playlists = JSON.parse(playlistsString);
    console.debug('Restoring playlists state', playlists);
    for (const playlist of Object.values(state.playlists)) {
        const checkbox = document.getElementById('checkbox-' + playlist.name);
        if (checkbox) {
            checkbox.checked = playlists.indexOf(playlist.name) !== -1;
        }
    }
}

function savePlaylistState() {
    const checkedPlaylists = [];
    for (const playlist of Object.values(state.playlists)) {
        const checkbox = document.getElementById('checkbox-' + playlist.name);
        if (checkbox && checkbox.checked) {
            checkedPlaylists.push(playlist.name);
        }
    }
    console.debug('Saving playlists state', checkedPlaylists);
    localStorage.setItem('playlists', JSON.stringify(checkedPlaylists));
}
