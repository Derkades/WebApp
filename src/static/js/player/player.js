function seekRelative(delta) {
    const audioElem = getAudioElement();

    const newTime = audioElem.currentTime + delta;
    if (newTime < 0) {
        seekAbsolute(0);
    } else if (newTime > audioElem.duration) {
        seekAbsolute(audioElem.duration);
    } else {
        seekAbsolute(newTime);
    }
}

function seekAbsolute(position) {
    if (!isFinite(position)) {
        console.warn('Ignoring seek with non-finite position', position);
        return;
    }

    getAudioElement().currentTime = position;
    eventBus.publish(MusicEvent.PLAYBACK_CHANGE);
}

/**
 * @returns {HTMLAudioElement}
 */
function getAudioElement() {
    return document.getElementById('audio');
}

async function replaceAudioSource() {
    const sourceUrl = queue.currentTrack.audioBlobUrl;
    const audio = getAudioElement();
    audio.src = sourceUrl;
    // Ensure audio volume matches slider
    onVolumeChange();
    try {
        await audio.play();
    } catch (exception) {
        console.warn(exception);
    }
}

function replaceAlbumImages() {
    const imageUrl = queue.currentTrack.imageBlobUrl;

    const cssUrl = `url("${imageUrl}")`;

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

function replaceLyrics() {
    const queuedTrack = queue.currentTrack;
    const notFoundElem = document.getElementById('lyrics-not-found');
    const textElem = document.getElementById('lyrics-text');
    const sourceElem = document.getElementById('lyrics-source');
    if (queuedTrack.lyrics.found) {
        notFoundElem.classList.add('hidden');
        textElem.classList.remove('hidden');
        sourceElem.classList.remove('hidden');

        sourceElem.href = queuedTrack.lyrics.source;
        textElem.innerHTML = queuedTrack.lyrics.html + '<br>';
    } else {
        notFoundElem.classList.remove('hidden');
        textElem.classList.add('hidden');
        sourceElem.classList.add('hidden');
    }
    document.getElementById('lyrics-scroll').scrollTo({top: 0, behavior: 'smooth'});
}

function trackInfoUnavailableSpan() {
    const span = document.createElement('span');
    span.style.color = COLOR_MISSING_METADATA;
    span.textContent = '[track info unavailable]';
    return span;
}

function replaceTrackDisplayTitle() {
    if (queue.currentTrack !== null) {
        const track = queue.currentTrack.track();
        if (track !== null) {
            document.getElementById('current-track').replaceChildren(track.displayHtml(true));
            document.title = track.displayText(true);
        } else {
            document.getElementById('current-track').replaceChildren(trackInfoUnavailableSpan());
            document.title = '[track info unavailable]';
        }
    } else {
        // Nothing playing
        document.getElementById('current-track').textContent = '-';
    }

    const previous = queue.getPreviousTrack();
    if (previous !== null) {
        const previousTrack = previous.track();
        if (previousTrack !== null) {
            document.getElementById('previous-track').replaceChildren(previousTrack.displayHtml(true));
        } else {
            document.getElementById('previous-track').replaceChildren(trackInfoUnavailableSpan());
        }
    } else {
        document.getElementById('previous-track').textContent = '-';
    }
}

function replaceAllTrackHtml() {
    replaceAudioSource();
    replaceAlbumImages();
    replaceLyrics();
    replaceTrackDisplayTitle();
}

eventBus.subscribe(MusicEvent.TRACK_CHANGE, replaceAllTrackHtml);

// Update track title, metadata may have changed
eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, replaceTrackDisplayTitle);

function toggleLyrics() {
    if (document.getElementById('sidebar-lyrics').classList.contains('hidden')) {
        switchLyrics();
    } else {
        switchAlbumCover();
    }
}

/**
 * Display lyrics, hide album art
 */
function switchLyrics() {
    // document.getElementById('button-album').classList.remove('hidden');
    // document.getElementById('button-lyrics').classList.add('hidden');
    document.getElementById('sidebar-lyrics').classList.remove('hidden');
    document.getElementById('sidebar-album-covers').classList.add('hidden');
}

/**
 * Display album art, hide lyrics
 */
function switchAlbumCover() {
    // document.getElementById('button-album').classList.add('hidden');
    // document.getElementById('button-lyrics').classList.remove('hidden');
    document.getElementById('sidebar-lyrics').classList.add('hidden');
    document.getElementById('sidebar-album-covers').classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    // Lyrics / album cover switch buttons
    // document.getElementById('button-lyrics').addEventListener('click', switchLyrics);
    // document.getElementById('button-album').addEventListener('click', switchAlbumCover);
    // document.getElementById('button-album').classList.add('hidden');

    // Switch between album cover and lyrics by clicking in lyrics/cover
    document.getElementById('album-covers').addEventListener('click', event => {
        event.preventDefault();
        switchLyrics();
    });
    document.getElementById('lyrics-box').addEventListener('click', event => {
        if (event.target.nodeName === 'A') {
            // Allow clicking 'source' link
            return;
        }
        event.preventDefault();
        switchAlbumCover();
    });

    // Never play button
    document.getElementById('button-never-play').addEventListener('click', () => {
        const data = {track: queue.currentTrack.trackPath};
        jsonPost('/dislikes/add', data);
        queue.next();
    });

    // Delete track button
    const deleteButton = document.getElementById('button-delete-track');
    deleteButton.addEventListener('click', () => {
        if (queue.currentTrack === null) {
            return;
        }
        const deleteSpinner = document.getElementById('delete-spinner');
        deleteSpinner.classList.remove('hidden');
        const path = queue.currentTrack.trackPath;
        const oldName = path.split('/').pop();
        const newName = '.trash.' + oldName;
        (async function() {
            await jsonPost('/files/rename', {path: path, new_name: newName});
            await Track.updateLocalTrackList();
            queue.next();
            deleteSpinner.classList.add('hidden');
        })();
    });

    // Copy track to other playlist
    const copyOpenButton = document.getElementById('button-copy');
    if (copyOpenButton) { // Missing in offline mode
        const copyTrack = document.getElementById('copy-track');
        const copyPlaylist = document.getElementById('copy-playlist');
        const copyButton = document.getElementById('copy-do-button');
        copyOpenButton.addEventListener('click', () => {
            copyTrack.value = queue.currentTrack.path;
            dialogs.open('dialog-copy');
        });
        copyButton.addEventListener('click', async function() {
            copyButton.disabled = true;
            const response = await jsonPost('/player_copy_track', {playlist: copyPlaylist.value, track: queue.currentTrack.trackPath}, false);
            console.log(response.status);
            if (response.status == 200) {
                const text = await response.text();
                if (text != "") {
                    alert(text);
                }
            } else {
                alert('Error');
            }
            dialogs.close('dialog-copy');
            copyButton.disabled = false;
        });
    }

    queue.next();
});
