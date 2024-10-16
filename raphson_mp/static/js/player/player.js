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
        console.warn('player: ignoring seek with non-finite position', position);
        return;
    }

    getAudioElement().currentTime = position;
}

/**
 * @returns {HTMLAudioElement}
 */
function getAudioElement() {
    return document.getElementById('audio');
}

async function replaceAudioSource() {
    const audio = getAudioElement();
    audio.src = queue.currentTrack.audioUrl;
    // Ensure audio volume matches slider
    onVolumeChange();
    try {
        await audio.play();
    } catch (exception) {
        console.warn(exception);
    }
}

function replaceAlbumImages() {
    const imageUrl = queue.currentTrack.imageUrl;

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

    if (queuedTrack.lyrics && queuedTrack.lyrics.source) {
        sourceElem.classList.remove('hidden');
        sourceElem.href = queuedTrack.lyrics.source;
    } else {
        sourceElem.classList.add('hidden');
    }

    if (queuedTrack.lyrics) {
        notFoundElem.classList.add('hidden');
        textElem.classList.remove('hidden');
        textElem.textContent = queuedTrack.lyrics.lyrics;
    } else {
        notFoundElem.classList.remove('hidden');
        textElem.classList.add('hidden');
    }
}

function trackInfoUnavailableSpan() {
    const span = document.createElement('span');
    span.style.color = COLOR_MISSING_METADATA;
    span.textContent = '[track info unavailable]';
    return span;
}

function replaceTrackDisplayTitle() {
    if (queue.currentTrack !== null) {
        const track = queue.currentTrack.track;
        if (track !== null) {
            document.getElementById('current-track').replaceChildren(track.displayHtml(true));
            document.title = track.displayText(true, true);
        } else {
            document.getElementById('current-track').replaceChildren(trackInfoUnavailableSpan());
            document.title = '[track info unavailable]';
        }
    } else {
        // Nothing playing
        document.getElementById('current-track').textContent = '-';
    }
}

function replaceAllTrackHtml() {
    replaceAudioSource();
    replaceAlbumImages();
    replaceLyrics();
    replaceTrackDisplayTitle();

    document.getElementById('right-scroll').scrollTo({top: 0, behavior: 'smooth'});
}

eventBus.subscribe(MusicEvent.TRACK_CHANGE, replaceAllTrackHtml);

// Update track title, metadata may have changed
eventBus.subscribe(MusicEvent.METADATA_CHANGE, updatedTrack => {
    if (queue.currentTrack && queue.currentTrack.track.path && queue.currentTrack.track.path == updatedTrack.path) {
        console.debug('player: updating currently playing track following METADATA_CHANGE event');
        queue.currentTrack.track = updatedTrack;
    }
    replaceTrackDisplayTitle();
});

document.addEventListener('DOMContentLoaded', () => {
    const dislikeButton = document.getElementById('button-dislike')
    if (dislikeButton) { // Missing in offline mode
        dislikeButton.addEventListener('click', async function() {
            await queue.currentTrack.track.dislike();
            queue.next();
        });
    }

    const deleteButton = document.getElementById('button-delete');
    if (deleteButton) { // Missing in offline mode
        deleteButton.addEventListener('click', async function() {
            if (queue.currentTrack === null) {
                return;
            }
            const deleteSpinner = document.getElementById('delete-spinner');
            deleteSpinner.classList.remove('hidden');
            await queue.currentTrack.track.delete();
            queue.next();
            deleteSpinner.classList.add('hidden');
        });
    }

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
            try {
                await queue.currentTrack.track.copyTo(copyPlaylist.value);
            } catch (err) {
                console.error(err);
                alert('Error: ' + err);
            }
            dialogs.close('dialog-copy');
            copyButton.disabled = false;
        });
    }

    queue.next();
});

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('audio').addEventListener('ended', () => queue.next());
});
