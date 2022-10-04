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
    const track = findTrackByPath(path);

    if (track === null) {
        throw Error('Track does not exist in local list: ' + path);
    }

    await downloadAndAddToQueue(track);
}

async function downloadAndAddToQueue(track, top = false) {
    const encodedQuality = encodeURIComponent(document.getElementById('settings-audio-quality').value);
    const encodedPath = encodeURIComponent(track.path);

    // Get track audio
    console.info('queue | download audio');
    const trackResponse = await fetch('/get_track?path=' + encodedPath + '&quality=' + encodedQuality);
    checkResponseCode(trackResponse);
    const audioBlob = await trackResponse.blob();
    track.audioBlobUrl = URL.createObjectURL(audioBlob);

    // Get cover image
    if (encodedQuality === 'verylow') {
        console.info('queue | using raphson image to save data');
        track.imageUrl = '/raphson';
        track.imageBlobUrl = '/raphson';
    } else {
        console.info('queue | download album cover image');
        track.imageUrl = '/get_album_cover?path=' + encodedPath + '&quality=' + encodedQuality;
        const coverResponse = await fetch(track.imageUrl);
        checkResponseCode(coverResponse);
        const imageBlob = await coverResponse.blob();
        track.imageBlobUrl = URL.createObjectURL(imageBlob);
    }

    // Get lyrics
    if (encodedQuality === 'verylow') {
        track.lyrics = {
            found: true,
            source: null,
            html: "<i>Lyrics were not downloaded to save data</i>",
        };
    } else {
        console.info('queue | download lyrics');
        track.lyricsUrl = '/get_lyrics?path=' + encodedPath;
        const lyricsResponse = await fetch(track.lyricsUrl);
        checkResponseCode(lyricsResponse);
        const lyricsJson = await lyricsResponse.json();
        track.lyrics = lyricsJson;
    }

    // Add track to queue and update HTML
    if (top) {
        state.queue.unshift(track);
    } else {
        state.queue.push(track);
    }
    updateQueueHtml();
    console.info("queue | done");
}

function removeFromQueue(index) {
    const track = state.queue[index];
    const removalBehaviour = document.getElementById('settings-queue-removal-behaviour').value;
    if (removalBehaviour === 'same') {
        state.playlistOverrides.push(track.playlist);
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
        const tdCover = document.createElement('td');
        tdCover.classList.add('box-rounded');
        tdCover.style.backgroundImage = 'url("' + queuedTrack.imageBlobUrl + '")';
        const rememberI = i;
        tdCover.onclick = () => removeFromQueue(rememberI);
        const deleteOverlay = document.createElement('div');
        deleteOverlay.classList.add('delete-overlay');
        const deleteDiv = document.createElement('div');
        deleteDiv.style.backgroundImage = "url('/static/icon/delete.svg')";
        deleteDiv.classList.add('icon');
        deleteOverlay.appendChild(deleteDiv);
        tdCover.appendChild(deleteOverlay);

        const tdPlaylist = document.createElement('td');
        tdPlaylist.textContent = queuedTrack.playlist_display;

        const tdTrack = document.createElement('td');
        tdTrack.appendChild(getTrackDisplayHtml(queuedTrack));

        const row = document.createElement('tr');
        row.dataset.queuePos = i;
        row.appendChild(tdCover);
        row.appendChild(tdPlaylist);
        row.appendChild(tdTrack);

        rows.push(row);
        i++;
    }

    const minQueueSize = parseInt(document.getElementById('settings-queue-size').value)

    if (i < minQueueSize) {
        const td = document.createElement('td');
        td.colSpan = 3;
        td.classList.add('secondary', 'downloading');
        const spinner = document.createElement('span');
        spinner.classList.add('spinner');
        spinner.id = 'queue-spinner';
        td.appendChild(spinner);

        const row = document.createElement('tr');
        row.appendChild(td);

        rows.push(row);
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

        row.ondragstart = (ev) => {
            current = row;
            for (let it of items) {
                if (it != current) {
                    it.classList.add("hint");
                }
            }
        };

        row.ondragenter = (ev) => {
            if (row != current) {
                row.classList.add("active");
            }
        };

        row.ondragleave = () => {
            row.classList.remove("active");
        };

        row.ondragend = () => {
            for (let it of items) {
                it.classList.remove("hint");
                it.classList.remove("active");
            }
        };

        row.ondragover = (evt) => {
            evt.preventDefault();
        };

        row.ondrop = (evt) => {
            evt.preventDefault();
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

function searchTrackList() {
    if (state.tracks === null) {
        document.getElementById('track-list-output').textContent = 'Track list is still loading, please wait... If this takes longer than 10 seconds, please check the console for errors.';
        return;
    }

    const playlist = document.getElementById('track-list-playlist').value;
    const query = document.getElementById('track-list-query').value.trim().toLowerCase();

    const scoredTracks = [];

    for (const track of state.tracks) {
        if (playlist === 'everyone' || playlist === track.playlist) {
            let score = 0;

            if (query !== '') {
                score += track.path.length - levenshtein(track.path.toLowerCase(), query);
                score += track.display.length - levenshtein(track.display.toLowerCase(), query);

                // Boost exact matches
                if (track.path.toLowerCase().includes(query)) {
                    score *= 2;
                }

                if (track.display.toLowerCase().includes(query)) {
                    score *= 2;
                }
            } else {
                // No query, display all
                score = 1;
            }

            if (score > 0) {
                scoredTracks.push({
                    score: score,
                    track: track,
                });
            }
        }
    }

    scoredTracks.sort((a, b) => b.score - a.score);

    const tracks = [];
    for (const scoredTrack of scoredTracks) {
        tracks.push(scoredTrack.track);
    }

    document.getElementById('track-list-output').replaceChildren(browse.generateTrackList(tracks))
}
