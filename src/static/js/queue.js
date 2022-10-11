function hideLoadingOverlay() {
    if (state.loadingOverlayHidden) {
        return;
    }
    state.loadingOverlayHidden = true;
    const overlay = document.getElementById('loading-overlay');
    overlay.style.opacity = 0;
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 500);
}

function updateQueue() {
    updateQueueHtml();

    if (state.queueBusy) {
        return;
    }

    let minQueueSize = parseInt(document.getElementById('settings-queue-size').value);

    if (!isFinite(minQueueSize)) {
        minQueueSize = 1;
    }

    if (state.queue.length >= minQueueSize) {
        return;
    }

    let playlist;

    if (state.playlistOverrides.length > 0) {
        playlist = state.playlistOverrides.pop();
        console.info('queue | override: ' + playlist)
    } else {
        playlist = getNextPlaylist(state.lastChosenPlaylist);
        console.info('queue | round robin: ' + state.lastChosenPlaylist + ' -> ' + playlist)
        state.lastChosenPlaylist = playlist;
    }

    if (playlist === null) {
        console.info('queue | no playlists selected, trying again later');
        // TODO Display warning in queue
        setTimeout(updateQueue, 500);
        return;
    }

    state.queueBusy = true;

    downloadRandomAndAddToQueue(playlist).then(() => {
        state.queueBusy = false;
        updateQueue();
    }, error => {
        console.warn('queue | error');
        console.warn(error);
        state.queueBusy = false
        setTimeout(updateQueue, 5000);
    });
}

async function downloadRandomAndAddToQueue(playlist) {
    console.info('queue | choose track');
    const chooseResponse = await fetch('/choose_track?playlist_dir=' + encodeURIComponent(playlist) + '&' + getTagFilter());
    checkResponseCode(chooseResponse);
    const path = (await chooseResponse.json()).path;

    // Find track info for this file
    const track = Track.findTrackByPath(path);

    if (track === null) {
        throw Error('Track does not exist in local list: ' + path);
    }

    await track.downloadAndAddToQueue();
}

function removeFromQueue(index) {
    const track = state.queue[index];
    const removalBehaviour = document.getElementById('settings-queue-removal-behaviour').value;
    if (removalBehaviour === 'same') {
        // Add playlist to override array. Next time a track is picked, when playlistOverrides contains elements,
        // one element is popped and used instead of choosing a random playlist.
        state.playlistOverrides.push(track.playlistPath);
    } else if (removalBehaviour !== 'roundrobin') {
        console.warn('unexpected removal behaviour: ' + removalBehaviour);
    }
    state.queue.splice(index, 1);
    updateQueueHtml();
    updateQueue();
}

function updateQueueHtml() {
    document.getElementsByTagName("body")[0].style.cursor = state.queueBusy ? 'progress' : '';

    let totalQueueDuration = 0;
    for (const queuedTrack of state.queue) {
        totalQueueDuration += queuedTrack.duration;
    }

    document.getElementById('current-queue-size').textContent = state.queue.length + ' - ' + secondsToString(totalQueueDuration);

    const rows = [];
    let i = 0;
    for (const queuedTrack of state.queue) {
        // Trash can that appears when hovering - click to remove track
        const tdCover = document.getElementById('template-td-cover').content.cloneNode(true).firstElementChild;
        tdCover.style.backgroundImage = 'url("' + queuedTrack.imageBlobUrl + '")';
        const rememberI = i;
        tdCover.onclick = () => removeFromQueue(rememberI);

        // Playlist link that opens browse view
        const aPlaylist = document.createElement('a');
        aPlaylist.textContent = queuedTrack.playlistDisplay;
        aPlaylist.onclick = () => browse.browsePlaylist(queuedTrack.playlistPath);
        const tdPlaylist = document.createElement('td');
        tdPlaylist.append(aPlaylist);

        // Track title HTML
        const tdTrack = document.createElement('td');
        tdTrack.appendChild(queuedTrack.displayHtml());

        // Add columns to <tr> row and add the row to the table
        const row = document.createElement('tr');
        row.dataset.queuePos = i;
        row.appendChild(tdCover);
        row.appendChild(tdPlaylist);
        row.appendChild(tdTrack);

        rows.push(row);
        i++;
    }

    // If the queue is still loading (size smaller than target size), add a loading spinner
    const minQueueSize = parseInt(document.getElementById('settings-queue-size').value);
    if (i < minQueueSize) {
        rows.push(document.getElementById('template-queue-spinner').content.cloneNode(true));
    }

    const outerDiv = document.getElementById('queue-table');
    outerDiv.replaceChildren(...rows);
    // Add events to <tr> elements
    dragDropTable(document.getElementById("queue-table"));
}

// Based on https://code-boxx.com/drag-drop-sortable-list-javascript/
// Modified to work with table and state.queue
function dragDropTable(target) {
    let items = target.getElementsByTagName("tr");
    let current = null; // Element that is being dragged

    for (let row of items) {
        row.draggable = true; // Make draggable

        // The .hint and .active classes are purely cosmetic, they may be styled using css

        row.ondragstart = () => {
            current = row;
            for (let it of items) {
                if (it != current) {
                    it.classList.add("hint");
                }
            }
        };

        row.ondragenter = () => {
            if (row != current) {
                row.classList.add("active");
            }
        };

        row.ondragleave = () => row.classList.remove("active");

        row.ondragend = () => {
            for (let it of items) {
                it.classList.remove("hint");
                it.classList.remove("active");
            }
        };

        row.ondragover = event => event.preventDefault();

        row.ondrop = (event) => {
            event.preventDefault();

            if (row == current) {
                // No need to do anything if row was put back in same location
                return;
            }

            const currentPos = current.dataset.queuePos;
            const targetPos = row.dataset.queuePos;
            // Remove current (being dragged) track from queue
            const track = state.queue.splice(currentPos, 1)[0];
            // Add it to the place it was dropped
            state.queue.splice(targetPos, 0, track);
            // Now re-render the table
            updateQueueHtml();
        };
    }
}
