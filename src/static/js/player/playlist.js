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

function createPlaylistCheckbox(playlist, index) {
    const span = document.createElement("span");
    span.classList.add("checkbox-with-label");

    const input = document.createElement("input");
    input.type = 'checkbox';
    input.classList.add('playlist-checkbox');
    input.id = 'checkbox-' + playlist.dir_name;
    // Attempt to restore state from cookie
    const savedState = getSavedCheckboxState();
    if (savedState === null) {
        // No save state, enable if it's a favorited playlist
        input.checked = playlist.favorite
    } else {
        input.checked = savedState.indexOf(playlist.dir_name) !== -1;
    }
    input.onclick = saveCheckboxState;

    const label = document.createElement("label");
    label.htmlFor = "checkbox-" + playlist.dir_name;
    label.textContent = playlist.display_name;
    const sup = document.createElement('sup');
    if (index < 10) { // Assume number keys higher than 9 don't exist
        sup.textContent = index;
    }
    label.replaceChildren(
        playlist.display_name,
        sup,
        ' (' + playlist.track_count + ')'
    );

    span.appendChild(input);
    span.appendChild(label);

    return span;
}

function updatePlaylistCheckboxHtml() {
    let index = 1;
    const mainDiv = document.createElement('div');
    for (const playlist of state.mainPlaylists) {
        mainDiv.appendChild(createPlaylistCheckbox(playlist, index++));
    }
    const otherDiv = document.createElement('div');
    otherDiv.classList.add('other-checkboxes');
    for (const playlist of state.otherPlaylists) {
        otherDiv.appendChild(createPlaylistCheckbox(playlist, 10));
    }
    const parent = document.getElementById('playlist-checkboxes');
    parent.replaceChildren(mainDiv, otherDiv);
}

function saveCheckboxState() {
    setCookie('enabled-playlists', getActivePlaylists().join('~'));
}

function getSavedCheckboxState() {
    const cookie = getCookie('enabled-playlists');
    if (cookie === null) {
        return null;
    } else {
        return cookie.split('~');
    }
}

function createPlaylistDropdowns() {
    for (const select of document.getElementsByClassName("playlist-select")) {
        // Remove all children except the ones that should be kept
        const keptChildren = []
        for (const child of select.children) {
            if (child.dataset.keep === 'true') {
                keptChildren.push(child);
                continue;
            }
        }
        select.replaceChildren(...keptChildren);

        for (const dir_name in state.playlists) {
            const playlist = state.playlists[dir_name];
            const option = document.createElement('option');
            option.value = playlist.dir_name;
            option.textContent = playlist.display_name;
            select.appendChild(option);
        }
    }
}
