function hideLoadingOverlay() {
    if (state.loadingOverlayHidden) {
        return;
    }
    state.loadingOverlayHidden = true;
    const overlay = document.getElementById('loading-overlay');
    overlay.style.opacity = 0;
    setTimeout(() => {
        overlay.style.display = 'none';
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

    const trackData = {
        playlist: playlist,
        playlist_display: playlist.startsWith("Guest-") ? playlist.substring('6') : playlist,
        file: null, // choose random
    }

    downloadAndAddToQueue(trackData).then(() => {
        state.queueBusy = false;
        updateQueue();
    }, error => {
        console.warn('queue | error');
        console.warn(error);
        state.queueBusy = false
        setTimeout(updateQueue, 5000);
    });
}

async function downloadAndAddToQueue(track, top=false) {
    // If no specific track is specified, first choose random track
    if (track.file === null) {
        console.info('queue | choose track');
        const chooseResponse = await fetch('/choose_track?playlist_dir=' + encodeURIComponent(track.playlist));
        checkResponseCode(chooseResponse);
        const trackJson = await chooseResponse.json();
        track.file = trackJson.file;
        track.display = trackJson.display;
        track.duration = trackJson.duration;
    }

    // Get track audio
    console.info('queue | download audio');
    const encodedQuality = encodeURIComponent(document.getElementById('settings-audio-quality').value);
    const trackResponse = await fetch('/get_track?path=' + encodeURIComponent(track.file) + '&quality=' + encodedQuality);
    checkResponseCode(trackResponse);
    const audioBlob = await trackResponse.blob();
    track.audioBlobUrl = URL.createObjectURL(audioBlob);

    // Get cover image
    if (encodedQuality === 'verylow') {
        console.info('queue | using raphson image to save data');
        track.imageStreamUrl = '/raphson';
        track.imageBlobUrl = '/raphson';
    } else {
        console.info('queue | download album cover image');
        track.imageStreamUrl = '/get_album_cover?path=' + encodeURIComponent(track.file);
        const coverResponse = await fetch(track.imageStreamUrl);
        checkResponseCode(coverResponse);
        const imageBlob = await coverResponse.blob();
        track.imageBlobUrl = URL.createObjectURL(imageBlob);
    }

    // Get lyrics
    if (encodedQuality === 'verylow') {
        track.lyrics = {
            found: true,
            genius_url: null,
            html: "<i>Lyrics were not downloaded to save data</i>",
        };
    } else {
        console.info('queue | download lyrics');
        track.lyricsUrl = '/get_lyrics?path=' + encodeURIComponent(track.file);
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
    hideLoadingOverlay();
    console.info("queue | done");
}

function removeFromQueue(index) {
    const trackData = state.queue[index];
    const removalBehaviour = document.getElementById('settings-queue-removal-behaviour').value;
    if (removalBehaviour === 'same') {
        state.playlistOverrides.push(trackData.playlist);
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

    const trashBase64 = document.getElementById('delete-base64').innerText;

    let html = ''
    let i = 0;
    for (const queuedTrack of state.queue) {
        html += '<tr data-queue-pos="' + i + '">';
            html += '<td class="box" style="background-image: url(\'' + escapeHtml(queuedTrack.imageBlobUrl) + '\')" onclick="removeFromQueue(' + i + ')">';
                html += '<div class="delete-overlay">'
                    html += '<div style="background-image: url(\'' + trashBase64 + '\')" class="icon"></div>';
                html += '</div>'
            html += '</td>';
            html += '<td>' + queuedTrack.playlist_display + '</td>';
            html += '<td>' + escapeHtml(queuedTrack.display) + '</td>';
        html += '</tr>';
        i++;
    }

    const minQueueSize = parseInt(document.getElementById('settings-queue-size').value)

    let first = true;
    while (i < minQueueSize) {
        html += '<tr data-queue-pos="' + i + '">'
        html += '<td colspan="3" class="secondary downloading">';
        if (first) {
            first = false;
            html += '<span class="spinner" id="queue-spinner"></span>';
        }
        html += '</td></tr>';
        i++;
    }

    const outerDiv = document.getElementById('queue-table');
    outerDiv.innerHTML = html;
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
        document.getElementById('track-list-output').textContent = 'Track list is still loading, please wait... If this takes longer than a minute, please check the console for errors.';
        return;
    }

    const playlist = document.getElementById('track-list-playlist').value;
    const query = document.getElementById('track-list-query').value.trim().toLowerCase();

    const tracks = [];

    for (const track of state.tracks) {
        if (playlist === 'everyone' || playlist === track.playlist) {
            let score = 0;

            if (query !== '') {
                score += track.file.length - levenshtein(track.file.toLowerCase(), query);
                score += track.display.length - levenshtein(track.display.toLowerCase(), query);

                // Boost exact matches
                if (track.file.toLowerCase().includes(query)) {
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
                tracks.push({
                    playlistDir: track.playlist,
                    playlistDisplay: track.playlist_display,
                    trackFile: track.file,
                    trackDisplay: track.display,
                    score: score,
                });
            }
        }
    }

    tracks.sort((a, b) => b.score - a.score);

    let i = 0;
    let outputHtml = '';
    for (const track of tracks) {
        outputHtml += ''
            + '<button '
            + 'id="queue-choice-' + i + '" '
            + 'data-track="' + escapeHtml(track.trackFile) + '" '
            + 'onclick="searchTrackListQueueAdd(this.id);">'
            + '[' + escapeHtml(track.playlistDisplay) + '] ' + escapeHtml(track.trackDisplay)
            + '</button><br>';


        if (i > state.maxSearchListSize) {
            outputHtml += '...';
            break;
        }

        i++;
    }

    document.getElementById('track-list-output').innerHTML = outputHtml;
}

function searchTrackListQueueAdd(id) {
    const button = document.getElementById(id);
    const file = button.dataset.track;
    const track = findTrackByFile(file);

    if (track === null) {
        console.error('track not found in track list: ' + file);
        return;
    }

    downloadAndAddToQueue(track, true);
    document.getElementById('queue-overlay').style.display = 'none';
}
