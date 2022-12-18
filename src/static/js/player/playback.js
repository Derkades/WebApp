function play() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    audioElem.play().then(updateMediaSession);
}

function pause() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    audioElem.pause()
    updateMediaSession()
}

function playPause() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    if (audioElem.paused) {
        play();
    } else {
        pause();
    }
}

// Called periodically (frequently). Also called manually on some events like play/pause/seek.
function updateMediaSession() {
    const audioElem = getAudioElement();

    const oldState = navigator.mediaSession.playbackState;
    const newState = audioElem == null ? 'none' : (audioElem.paused ? 'paused' : 'playing');

    if (newState != oldState) {
        navigator.mediaSession.playbackState = newState;
        if (newState == 'playing') {
            document.getElementById('button-play').style.display = 'none';
            document.getElementById('button-pause').style.display = '';
        } else {
            document.getElementById('button-pause').style.display = 'none';
            document.getElementById('button-play').style.display = '';
        }
    }

    if (audioElem != null && isFinite(audioElem.duration) && isFinite(audioElem.currentTime) && isFinite(audioElem.playbackRate)) {
        navigator.mediaSession.setPositionState({
            duration: audioElem.duration,
            playbackRate: audioElem.playbackRate,
            position: audioElem.currentTime,
        });

        const current = secondsToString(Math.floor(audioElem.currentTime));
        const max = secondsToString(Math.floor(audioElem.duration));
        const percentage = (audioElem.currentTime / audioElem.duration) * 100;

        document.getElementById('progress-bar').style.width = percentage + '%';
        document.getElementById('progress-time-current').innerText = current;
        if (newState != oldState && newState == 'playing') {
            // TODO move to updateMediaTrackInfo()
            document.getElementById('progress-time-duration').innerText = max;
        }
    } else {
        navigator.mediaSession.setPositionState({});
        document.getElementById('progress-bar').style.width = '0';
    }
}

// Called on track change
function updateMediaTrackInfo() {
    const track = queue.currentTrack;
    navigator.mediaSession.metadata = new MediaMetadata({
        title: track.title !== null ? track.title : track.display,
        album: track.album !== null ? track.album : 'Unknown Album',
        artist: track.artists !== null ? track.artists.join(' & ') : 'Unknown Artist',
        // For some unknown reason this does not work everywhere. For example, it works on Chromium
        // mobile and desktop, but not the KDE media player widget with Firefox or Chromium.
        // Firefox mobile doesn't seem to support the MediaSession API at all.
        artwork: [{src: track.imageBlobUrl}],
    });
}

function onTrackChange() {
    updateTrackHtml();
    updateMediaSession();
    updateMediaTrackInfo();
    lastfm.signalNewTrack();
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

    updateMediaSession();
}

// Seek to position in song, float 0 to 1
function seekToFloat(position) {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }

    audioElem.currentTime = position * audioElem.duration;

    updateMediaSession();
}

// Seek to position in song, current time in seconds
function seekToSeconds(position) {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }

    audioElem.currentTime = position;

    updateMediaSession();
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
    audioElem.onended = () => queue.next();
    const sourceElem = document.createElement('source');
    sourceElem.src = sourceUrl;
    audioElem.appendChild(sourceElem);
    return audioElem;
}

function getAudioElement() {
    const audioDiv = document.getElementById('audio');
    if (audioDiv.children.length === 1) {
        return audioDiv.children[0];
    }
    return null;
}

// Replace audio player, album cover, and lyrics according to current track info
function updateTrackHtml() {
    const track = queue.currentTrack;
    const audioElem = createAudioElement(track.audioBlobUrl);
    replaceAudioElement(audioElem);

    replaceAlbumImages(track.imageBlobUrl);

    const notFoundElem = document.getElementById('lyrics-not-found');
    const textElem = document.getElementById('lyrics-text');
    const sourceElem = document.getElementById('lyrics-source');
    if (track.lyrics.found) {
        notFoundElem.classList.add('hidden');
        textElem.classList.remove('hidden');
        sourceElem.classList.remove('hidden');

        sourceElem.href = track.lyrics.source;
        textElem.innerHTML = track.lyrics.html;
    } else {
        notFoundElem.classList.remove('hidden');
        textElem.classList.add('hidden');
        sourceElem.classList.add('hidden');
    }
    document.getElementById('lyrics-scroll').scrollTo({top: 0, behavior: 'smooth'});

    document.getElementById('current-track').replaceChildren(track.displayHtml(true));

    const previous = queue.getPreviousTrack();
    if (previous !== null) {
        document.getElementById('previous-track').replaceChildren(previous.displayHtml(true));
    } else {
        document.getElementById('previous-track').textContent = '-';
    }
}

function replaceAudioElement(newElement) {
    const audioDiv = document.getElementById('audio');
    audioDiv.replaceChildren(newElement);
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
    document.getElementById('button-album').classList.remove('hidden');
    document.getElementById('button-lyrics').classList.add('hidden');
    document.getElementById('sidebar-lyrics').classList.remove('hidden');
    document.getElementById('sidebar-album-covers').classList.add('hidden');
}

// Display album art, instead of lyrics
function switchAlbumCover() {
    document.getElementById('button-album').classList.add('hidden');
    document.getElementById('button-lyrics').classList.remove('hidden');
    document.getElementById('sidebar-lyrics').classList.add('hidden');
    document.getElementById('sidebar-album-covers').classList.remove('hidden');
}
