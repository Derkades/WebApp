document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();

    // Home
    const homeButton = document.getElementById('button-home');
    if (homeButton) {
        homeButton.addEventListener('click', () => window.open('/', '_blank'));
    }

    // Skip to previous
    document.getElementById('button-prev').addEventListener('click', () => {
        // Try to skip to beginning of current track first
        if (audioElem.currentTime > 15 || queue.previousTracks.length == 0) {
            audioElem.currentTime = 0;
            return;
        }

        queue.previous();
    });

    // Skip to next
    document.getElementById('button-next').addEventListener('click', () => queue.next());

    // Play pause
    document.getElementById('button-play').addEventListener('click', () => {
        audioElem.play();
    });
    document.getElementById('button-pause').addEventListener('click', () => {
        audioElem.pause();
    });

    // Seek bar
    const seekBar = document.getElementById('outer-progress-bar');

    const onMove = event => {
        const audioElem = getAudioElement();
        audioElem.currentTime = ((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * audioElem.duration;
        event.preventDefault(); // Prevent accidental text selection
    };

    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    };

    seekBar.addEventListener('mousedown', event => {
        const audioElem = getAudioElement();
        seekAbsolute(((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * audioElem.duration);

        // Keep updating while mouse is moving
        document.addEventListener('mousemove', onMove);

        // Unregister events on mouseup event
        document.addEventListener('mouseup', onUp);

        event.preventDefault(); // Prevent accidental text selection
    });

    // Scroll to seek
    seekBar.addEventListener('wheel', event => {
        seekRelative(event.deltaY < 0 ? 3 : -3);
    }, {passive: true});

    hideButtons();
});

function hideButtons() {
    if (!document.getElementById('button-dislike')) {
        // if dislike button does not exist, we are running in offline mode and other buttons also don't exist
        return;
    }

    document.getElementById('button-edit').classList.add('hidden');
    document.getElementById('button-delete').classList.add('hidden');
    document.getElementById('button-dislike').classList.add('hidden');
}

// Update seek bar
function updateSeekBar() {
    // Save resources updating seek bar if it's not visible
    if (document.visibilityState != 'visible') {
        return;
    }

    const audioElem = getAudioElement();

    var barCurrent;
    var barDuration;
    var barWidth;

    if (isFinite(audioElem.currentTime) && isFinite(audioElem.duration)) {
        barCurrent = durationToString(Math.round(audioElem.currentTime));
        barDuration = durationToString(Math.round(audioElem.duration));
        barWidth = ((audioElem.currentTime / audioElem.duration) * 100) + '%';
    } else {
        barCurrent = '--:--';
        barDuration = '--:--';
        barWidth = 0;
    }

    document.getElementById('progress-time-current').innerText = barCurrent;
    document.getElementById('progress-time-duration').innerText = barDuration;
    document.getElementById('progress-bar').style.width = barWidth
}

// Update play/pause buttons
function updatePlayPauseButtons() {
    if (getAudioElement().paused) {
        document.getElementById('button-pause').classList.add('hidden');
        document.getElementById('button-play').classList.remove('hidden');
    } else {
        document.getElementById('button-pause').classList.remove('hidden');
        document.getElementById('button-play').classList.add('hidden');
    }
}

// Only show metadata edit and track delete buttons if playlist is writable
eventBus.subscribe(MusicEvent.TRACK_CHANGE, async function() {
    if (!document.getElementById('button-dislike')) {
        // if dislike button does not exist, we are running in offline mode and other buttons also don't exist
        return;
    }

    const track = queue.currentTrack.track;

    // Show dislike button if track is real (e.g. not a virtual news track)
    const showDislike = track !== null;
    const showEditDelete = track !== null && (await music.playlist(track.playlistName)).write;

    if (showDislike) {
        document.getElementById('button-dislike').classList.remove('hidden');
    } else {
        document.getElementById('button-dislike').classList.add('hidden');
    }

    if (showEditDelete) {
        document.getElementById('button-edit').classList.remove('hidden');
        document.getElementById('button-delete').classList.remove('hidden');
    } else {
        document.getElementById('button-edit').classList.add('hidden');
        document.getElementById('button-delete').classList.add('hidden');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    getAudioElement().addEventListener('durationchange', updateSeekBar);
    getAudioElement().addEventListener('timeupdate', updateSeekBar);
    getAudioElement().addEventListener('pause', updatePlayPauseButtons);
    getAudioElement().addEventListener('play', updatePlayPauseButtons);
    updatePlayPauseButtons();
    // Seek bar is not updated when page is not visible. Immediately update it when the page does become visibile.
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState == 'visible') {
            updateSeekBar();
        }
    });
});
