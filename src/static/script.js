"use strict";

// ##############################################
//           Configuration & state
// ##############################################

document.queue = [];
document.current = null;
document.history = [];
document.queueBusy = false;
document.historySize = 10;
document.maxSearchListSize = 500;
document.lastChosenPlaylist = null;
document.playlistOverrides = [];
document.playlists = null;
document.mainPlaylists = [];
document.guestPlaylists = [];
document.tracks = null;

// ##############################################
//                Initialization
// ##############################################

document.addEventListener("DOMContentLoaded", () => {
    syncCookiesWithInputs();

    // Playback controls
    document.getElementById('button-backward-step').addEventListener('click', previous);
    // document.getElementById('button-backward-fast').addEventListener('click', () => seek(-30));
    document.getElementById('button-backward').addEventListener('click', () => seek(-15));
    document.getElementById('button-play').addEventListener('click', play);
    document.getElementById('button-pause').addEventListener('click', pause);
    document.getElementById('button-forward').addEventListener('click', () => seek(15));
    // document.getElementById('button-forward-fast').addEventListener('click', () => seek(30));
    document.getElementById('button-forward-step').addEventListener('click', next);
    document.getElementById('settings-volume').addEventListener('input', event => {
        const audioElem = getAudioElement();
        if (audioElem !== null) {
            audioElem.volume = getTransformedVolume();
        }
    });

    // Queue
    updateQueue();

    // Lyrics
    document.getElementById('button-closed-captioning').addEventListener('click', switchLyrics);
    document.getElementById('button-record-vinyl').addEventListener('click', switchAlbumCover);
    document.getElementById('button-record-vinyl').style.display = 'none';

    // Settings overlay
    document.getElementById('button-gear').addEventListener('click', () =>
            document.getElementById('settings-overlay').style.display = 'flex');
    document.getElementById('settings-close').addEventListener('click', () =>
            document.getElementById('settings-overlay').style.display = 'none');
    document.getElementById('youtube-dl-submit').addEventListener('click', youTubeDownload);
    document.getElementById('settings-queue-size').addEventListener('input', () => updateQueue());

    // Queue overlay
    document.getElementById('button-square-plus').addEventListener('click', () =>
            document.getElementById('queue-overlay').style.display = 'flex');
    document.getElementById('queue-close').addEventListener('click', () =>
            document.getElementById('queue-overlay').style.display = 'none');
    document.getElementById('track-list-playlist').addEventListener('input', searchTrackList);
    document.getElementById('track-list-query').addEventListener('input', searchTrackList);

    // Hotkeys
    document.addEventListener('keydown', event => handleKey(event.key));

    setInterval(() => {
        if (document.queueBusy) {
            document.getElementsByTagName("body")[0].style.cursor = 'progress';
        } else {
            document.getElementsByTagName("body")[0].style.cursor = '';
        }
    }, 100);

    next();
    setInterval(showCorrectPlayPauseButton, 50);
    initTrackList();
    searchTrackList();
});

// ##############################################
//               Cookie loading
// ##############################################

function syncCookieWithInput(elemId) {
    // If cookie exists, set input value to cookie value
    const value = getCookie(elemId);
    if (value !== null) {
        document.getElementById(elemId).value = value;
    }

    // If input value is updated, set cookie accordingly
    document.getElementById(elemId).addEventListener('input', event => {
        setCookie(elemId, event.target.value);
    });
}

function syncCookiesWithInputs() {
    [
        'settings-queue-size',
        'settings-audio-quality',
        'settings-volume',
        'settings-queue-removal-behaviour',
    ].forEach(syncCookieWithInput);
}

// ##############################################
//                    Hotkeys
// ##############################################

function handleKey(key) {
    // Don't perform hotkey actions when user is typing in a text field
    if (document.activeElement.tagName === 'INPUT') {
        console.log('Ignoring keypress', key)
        return;
    }

    const keyInt = parseInt(key);
    if (!isNaN(keyInt)) {
        let index = 1;
        for (const checkbox of document.getElementsByClassName('playlist-checkbox')) {
            if (index === keyInt) {
                checkbox.checked = !checkbox.checked
                break;
            }
            index++;
        }
    } else if (key === 'p' || key === ' ') {
        playPause();
    } else if (key === 'ArrowLeft') {
        previous();
    } else if (key === 'ArrowRight') {
        next();
    } else if (key === '.') {
        seek(3);
    } else if (key === ',') {
        seek(-3);
    } else {
        console.log('Unhandled keypress', key)
    }
}

// ##############################################
//        Audio element & playback controls
// ##############################################

function getAudioElement() {
    const audioDiv = document.getElementById('audio');
    if (audioDiv.children.length === 1) {
        return audioDiv.children[0];
    }
    return null;
}

function replaceAudioElement(newElement) {
    const audioDiv = document.getElementById('audio');
    audioDiv.innerHTML = '';
    audioDiv.appendChild(newElement);
}

function play() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    audioElem.play();
}

function pause() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    audioElem.pause();
}

function playPause() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    if (audioElem.paused) {
        audioElem.play();
    } else {
        audioElem.pause();
    }
}

function showCorrectPlayPauseButton() {
    const audioElem = getAudioElement();
    if (audioElem == null || audioElem.paused) {
        document.getElementById('button-pause').style.display = 'none';
        document.getElementById('button-play').style.display = '';
    } else {
        document.getElementById('button-play').style.display = 'none';
        document.getElementById('button-pause').style.display = '';
    }
}

function seek(delta) {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    const newTime = audioElem.currentTime + delta;
    if (newTime < 0) {
        audioElem.currentTime = 0;
    } else if (newTime > audioElem.duration) {
        audioElem.currentTime = audioElem.duration;
    } else {
        audioElem.currentTime = newTime;
    }
}

function next() {
    if (document.queue.length === 0) {
        console.log('music | queue is empty, trying again later');
        setTimeout(next, 1000);
        return;
    }

    // Add current track to history
    if (document.current !== null) {
        document.history.push(document.current);
        // If history exceeded maximum length, remove first (oldest) element
        if (document.history.length > document.historySize) {
            document.history.shift();
        }
    }

    // Replace current track with first item from queue
    document.current = document.queue.shift();

    updateQueue();
    updateTrackHtml();
}

function previous() {
    const audioElem = getAudioElement();

    // Skip to beginning of current track first
    if (audioElem !== null && (audioElem.currentTime > 15 || document.history.length == 0)) {
        audioElem.currentTime = 0;
        return;
    }

    if (document.history.length == 0) {
        return;
    }

    // Move current track to beginning of queue
    document.queue.unshift(document.current);
    // Replace current track with last track in history
    document.current = document.history.pop();

    updateQueue();
    updateTrackHtml();
}

// ##############################################
//      Album cover, lyrics and audio HTML
// ##############################################

// Replace audio player, album cover, and lyrics according to document.current track info
function updateTrackHtml() {
    const track = document.current;
    const audioElem = createAudioElement(track.audioBlobUrl);
    replaceAudioElement(audioElem);

    replaceAlbumImages(track.imageBlobUrl);

    if (track.lyrics.found) {
        // track.lyrics.html is already escaped by backend, and only contains some safe HTML that we should not escape
        const source = '<a class="secondary" href="' + escapeHtml(track.lyrics.genius_url) + '" target="_blank">Source</a>'
        document.getElementById('lyrics').innerHTML = track.lyrics.html + '<br><br>' + source;
    } else {
        document.getElementById('lyrics').innerHTML = '<i class="secondary">Geen lyrics gevonden</i>'
    }

    document.getElementById('current-track').textContent = '[' + track.playlistDisplay + '] ' + track.displayName;

    if (document.history.length > 0) {
        const previousTrack = document.history[document.history.length - 1];
        document.getElementById('previous-track').textContent = '[' + previousTrack.playlistDisplay + '] ' + previousTrack.displayName;
    } else {
        document.getElementById('previous-track').textContent = '-';
    }
}

function updateProgress(audioElem) {
    const current = secondsToString(Math.floor(audioElem.currentTime));
    const max = secondsToString(Math.floor(audioElem.duration));
    const percentage = (audioElem.currentTime / audioElem.duration) * 100;

    document.getElementById('progress-time-current').innerText = current;
    document.getElementById('progress-time-duration').innerText = max;
    document.getElementById('progress-bar').style.width = percentage + '%';
}

function getTransformedVolume() {
    // https://www.dr-lex.be/info-stuff/volumecontrols.html
    // According to this article, x^4 seems to be a pretty good approximation of the perceived loudness curve
    const e = 4;
    return document.getElementById('settings-volume').value ** e / 100 ** e;
}

function createAudioElement(sourceUrl) {
    const audioElem = document.createElement('audio');
    audioElem.volume = getTransformedVolume();
    audioElem.setAttribute('autoplay', '');
    audioElem.onended = next;
    audioElem.ontimeupdate = () => updateProgress(audioElem);
    const sourceElem = document.createElement('source');
    sourceElem.src = sourceUrl;
    audioElem.appendChild(sourceElem);
    return audioElem;
}

function replaceAlbumImages(imageUrl) {
    const cssUrl = 'url("' + imageUrl + '")';

    const bgBottom = document.getElementById('bg-image-1');
    const bgTop = document.getElementById('bg-image-2');
    const fgBottom = document.getElementById('album-cover-1');
    const fgTop = document.getElementById('album-cover-2');

    // Set bottom to new image
    bgBottom.style.backgroundImage = cssUrl;
    fgBottom.style.backgroundImage = cssUrl;

    // Slowly fade out old top image
    bgTop.style.opacity = 0;
    fgTop.style.opacity = 0;

    setTimeout(() => {
        // To prepare for next replacement, move bottom image to top image
        bgTop.style.backgroundImage = cssUrl;
        fgTop.style.backgroundImage = cssUrl;
        // Make it visible
        bgTop.style.opacity = 1;
        fgTop.style.opacity = 1;
    }, 200);
}

// Display lyrics, instead of album art
function switchLyrics() {
    document.getElementById('button-record-vinyl').style.display = '';
    document.getElementById('button-closed-captioning').style.display = 'none';
    document.getElementById('sidebar-lyrics').style.display = 'flex';
    document.getElementById('sidebar-album-covers').style.display = 'none';
}

// Display album art, instead of lyrics
function switchAlbumCover() {
    document.getElementById('button-record-vinyl').style.display = 'none';
    document.getElementById('button-closed-captioning').style.display = '';
    document.getElementById('sidebar-lyrics').style.display = 'none';
    document.getElementById('sidebar-album-covers').style.display = 'flex';
}

// ##############################################
//              Queue (playlists)
// ##############################################

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

// ##############################################
//           Queue (downloading tracks)
// ##############################################

function updateQueue() {
    updateQueueHtml();

    if (document.queueBusy) {
        return;
    }

    let minQueueSize = parseInt(document.getElementById('settings-queue-size').value);

    if (!isFinite(minQueueSize)) {
        minQueueSize = 1;
    }

    if (document.queue.length >= minQueueSize) {
        return;
    }

    let playlist;

    if (document.playlistOverrides.length > 0) {
        playlist = document.playlistOverrides.pop();
        console.info('queue | override: ' + playlist)
    } else {
        playlist = getNextPlaylist(document.lastChosenPlaylist);
        console.info('queue | round robin: ' + document.lastChosenPlaylist + ' -> ' + playlist)
        document.lastChosenPlaylist = playlist;
    }

    if (playlist === null) {
        console.info('queue | no playlists selected, trying again later');
        // TODO Display warning in queue
        setTimeout(updateQueue, 500);
        return;
    }

    document.queueBusy = true;

    const trackData = {
        playlist: playlist,
        playlistDisplay: playlist.startsWith("Guest-") ? playlist.substring('6') : playlist,
        path: null, // choose random
    }

    downloadAndAddToQueue(trackData).then(() => {
        document.queueBusy = false;
        updateQueue();
    }, error => {
        console.warn('queue | error');
        console.warn(error);
        document.queueBusy = false
        setTimeout(updateQueue, 5000);
    });
}

async function downloadAndAddToQueue(trackData) {
    // If no specific track is specified, first choose random track
    if (trackData.path === null) {
        console.info('queue | choose track');
        const chooseResponse = await fetch('/choose_track?playlist_dir=' + encodeURIComponent(trackData.playlist));
        checkResponseCode(chooseResponse);
        const trackJson = await chooseResponse.json();
        trackData.path = trackJson.path;
        trackData.displayName = trackJson.display_name;
    }

    // Get track audio
    console.info('queue | download audio');
    const encodedQuality = encodeURIComponent(document.getElementById('settings-audio-quality').value);
    const encodedPath = encodeURIComponent(trackData.path);
    const trackResponse = await fetch('/get_track?track_path=' + encodedPath + '&quality=' + encodedQuality);
    checkResponseCode(trackResponse);
    const audioBlob = await trackResponse.blob();
    trackData.audioBlobUrl = URL.createObjectURL(audioBlob);

    // Get cover image
    console.info('queue | download album cover image');
    trackData.imageStreamUrl = '/get_album_cover?track_path=' + encodedPath;
    const coverResponse = await fetch(trackData.imageStreamUrl);
    checkResponseCode(coverResponse);
    const imageBlob = await coverResponse.blob();
    trackData.imageBlobUrl = URL.createObjectURL(imageBlob);

    // Get lyrics
    console.info('queue | download lyrics');
    trackData.lyricsUrl = '/get_lyrics?track_path=' + encodedPath;
    const lyricsResponse = await fetch(trackData.lyricsUrl);
    checkResponseCode(lyricsResponse);
    const lyricsJson = await lyricsResponse.json();
    trackData.lyrics = lyricsJson;

    // Finalize
    document.queue.push(trackData);
    updateQueueHtml();
    console.info("queue | done");
}

function removeFromQueue(index) {
    const trackData = document.queue[index];
    const removalBehaviour = document.getElementById('settings-queue-removal-behaviour').value;
    if (removalBehaviour === 'same') {
        document.playlistOverrides.push(trackData.playlist);
    } else if (removalBehaviour !== 'roundrobin') {
        console.warn('unexpected removal behaviour: ' + removalBehaviour);
    }
    document.queue.splice(index, 1);
    updateQueueHtml();
    updateQueue();
}

// ##############################################
//                  Queue HTML
// ##############################################

function updateQueueHtml() {
    const trashBase64 = document.getElementById('trash-can-base64').innerText;

    let html = ''
    let i = 0;
    for (const queuedTrack of document.queue) {
        html += '<tr data-queue-pos="' + i + '">';
            html += '<td class="background-cover box" style="background-image: url(\'' + escapeHtml(queuedTrack.imageBlobUrl) + '\')" onclick="removeFromQueue(' + i + ')">';
                html += '<div class="delete-overlay">'
                    html += '<div style="background-image: url(\'' + trashBase64 + '\')" class="icon"></div>';
                html += '</div>'
            html += '</td>';
            html += '<td>' + queuedTrack.playlistDisplay + '</td>';
            html += '<td>' + escapeHtml(queuedTrack.displayName) + '</td>';
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
// Modified to work with table and document.queue
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
            const track = document.queue.splice(currentPos, 1)[0];
            // Add it to the place it was dropped
            document.queue.splice(targetPos, 0, track);
            // Now re-render the table
            updateQueueHtml();
        };
    }
}

// ##############################################
//          Settings, YouTube download
// ##############################################

function youTubeDownload(event) {
    event.preventDefault();

    const output = document.getElementById('youtube-dl-output');
    output.style.backgroundColor = '';
    output.textContent = 'downloading...';

    const spinner = document.getElementById('youtube-dl-spinner');
    spinner.style.visibility = 'visible';

    const directory = document.getElementById('youtube-dl-directory').value;
    const url = document.getElementById('youtube-dl-url').value;

    const postBody = JSON.stringify({
        directory: directory,
        url: url,
    });

    const headers = new Headers({
        'Content-Type': 'application/json'
    });

    const options = {
        method: 'POST',
        body: postBody,
        headers: headers
    };

    fetch(new Request('/ytdl', options)).then(response => {
        if (response.status == 200) {
            spinner.style.visibility = 'hidden';
            response.json().then(json => {
                output.textContent = 'Status code: ' + json.code + '\n--- stdout ---\n' + json.stdout + '\n--- stderr ---\n' + json.stderr;
                output.style.backgroundColor = json.code === 0 ? 'lightgreen' : 'pink';
            });
        } else {
            response.text().then(alert);
        }
    });
}

// ##############################################
//          Track list, add to queue
// ##############################################

function initTrackList(skip = 0) {
    console.info('requesting track list, from track ' + skip);
    (async function() {
        const response = await fetch('/track_list?skip=' + skip);
        const json = await response.json();

        document.playlists = json.playlists;
        document.mainPlaylists = [];
        document.guestPlaylists = [];
        for (const dir_name in document.playlists) {
            // TODO sort alphabetically by display name
            const playlist = document.playlists[dir_name];
            if (playlist.guest) {
                document.guestPlaylists.push(playlist);
            } else {
                document.mainPlaylists.push(playlist);
            }
        }

        if (skip === 0) {
            document.tracks = json.tracks;
        } else {
            for (const track of json.tracks) {
                document.tracks.push(track);
            }
        }

        if (json.partial) {
            setTimeout(() => initTrackList(json.index + 1), 100);
        } else {
            setTimeout(initTrackList, 60_000)
        }

        // Update HTML depending on document.playlists and document.tracks
        updatePlaylistCheckboxHtml();
        searchTrackList();
    })().catch(err => {
        console.warn('track list | error');
        console.warn(err);
        setTimeout(initTrackList, 1000);
    });
}

function getCheckbox(playlist, index) {
    const span = document.createElement("span");
    span.classList.add("checkbox-with-label");

    const input = document.createElement("input");
    input.type = 'checkbox';
    input.classList.add('playlist-checkbox');
    input.id = 'checkbox-' + playlist.dir_name;
    // Attempt to restore state from cookie
    const savedState = getSavedCheckboxState();
    if (savedState === null) {
        // If no saved state, check if not guest
        input.checked = !playlist.guest
    } else {
        input.checked = savedState.indexOf(playlist.dir_name) !== -1;
    }
    input.onclick = saveCheckboxState;

    const label = document.createElement("label");
    label.attributes.for = "checkbox-" + playlist.dir_name;
    label.textContent = playlist.display_name;
    const sup = document.createElement('sup');
    sup.textContent = index;
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
    for (const playlist of document.mainPlaylists) {
        mainDiv.appendChild(getCheckbox(playlist, index++));
    }
    const guestDiv = document.createElement('div');
    guestDiv.classList.add('guest-checkboxes');
    for (const playlist of document.guestPlaylists) {
        guestDiv.appendChild(getCheckbox(playlist, index++));
    }
    const parent = document.getElementById('playlist-checkboxes');
    parent.replaceChildren(mainDiv, guestDiv);
}

function saveCheckboxState() {
    setCookie('enabled-playlists', getActivePlaylists().join('~'));
}

function getSavedCheckboxState() {
    const cookie = getCookie('enabled-playlists');
    if (cookie === null) {
        return null;
    } else {
        console.info('loading checkbox state: ' + cookie);
        return cookie.split('~');
    }
}

// TODO use this for track download and search dropdowns
function createPlaylistDropdown() {
    const select = document.createElement("select");
    for (const dir_name in document.playlists) {
        const playlist = document.playlists[dir_name];
        const option = document.createElement("option");
        option.value = playlist.dir_name;
        option.textContent = playlist.display_name;
        select.appendChild(option);
    }
    return select;
}

function queueAdd(id) {
    const button = document.getElementById(id);
    const trackData = {
        playlist: button.dataset.playlistDir,
        playlistDisplay: button.dataset.playlistDisplay,
        path: button.dataset.trackFile,
        displayName: button.dataset.trackDisplay,
    };
    downloadAndAddToQueue(trackData);
    document.getElementById('queue-overlay').style.display = 'none';
}

function searchTrackList() {
    if (document.tracks === null) {
        document.getElementById('track-list-output').textContent = 'Track list is still loading, please wait... If this takes longer than a minute, please check the console for errors.';
        return;
    }

    const playlist = document.getElementById('track-list-playlist').value;
    const query = document.getElementById('track-list-query').value.trim().toLowerCase();

    const tracks = [];

    for (const track of document.tracks) {
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
            + 'data-playlist-dir="' + escapeHtml(track.playlistDir) + '" '
            + 'data-playlist-display="' + escapeHtml(track.playlistDisplay) + '" '
            + 'data-track-file="' + escapeHtml(track.trackFile) + '" '
            + 'data-track-display="' + escapeHtml(track.trackDisplay) + '" '
            + 'onclick="queueAdd(this.id);">'
            + '[' + escapeHtml(track.playlistDisplay) + '] ' + escapeHtml(track.trackDisplay)
            + '</button><br>';


        if (i > document.maxSearchListSize) {
            outputHtml += '...en meer';
            break;
        }

        i++;
    }

    document.getElementById('track-list-output').innerHTML = outputHtml;
}

// ##############################################
//               Utility functions
// ##############################################

function choice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function checkResponseCode(response) {
    if (response.status != 200) {
        throw 'response code ' + response.status;
    }
}

function escapeHtml(unescaped) {
    const p = document.createElement("p");
    p.textContent = unescaped;
    return p.innerHTML;
}

function secondsToString(seconds) {
    // https://stackoverflow.com/a/25279399/4833737
    return new Date(1000 * seconds).toISOString().substring(14, 19);
}

// https://www.w3schools.com/js/js_cookies.asp
function setCookie(cname, cvalue) {
    const d = new Date();
    d.setTime(d.getTime() + (365*24*60*60*1000));
    const expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/;SameSite=Strict";
}

function getCookie(cname) {
    const name = cname + "=";
    const decodedCookie = decodeURIComponent(document.cookie);
    const ca = decodedCookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return null;
}

// https://www.tutorialspoint.com/levenshtein-distance-in-javascript
function levenshtein(str1, str2) {
    const track = Array(str2.length + 1).fill(null).map(() =>
    Array(str1.length + 1).fill(null));
    for (let i = 0; i <= str1.length; i += 1) {
       track[0][i] = i;
    }
    for (let j = 0; j <= str2.length; j += 1) {
       track[j][0] = j;
    }
    for (let j = 1; j <= str2.length; j += 1) {
       for (let i = 1; i <= str1.length; i += 1) {
          const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
          track[j][i] = Math.min(
             track[j][i - 1] + 1,
             track[j - 1][i] + 1,
             track[j - 1][i - 1] + indicator,
          );
       }
    }
    return track[str2.length][str1.length];
};
