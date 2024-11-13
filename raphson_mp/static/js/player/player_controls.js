document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();

    // Home
    const homeButton = document.getElementById('button-home');
    homeButton.addEventListener('click', () => window.open('/', '_blank'));

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
});

// Seek bar
document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();
    const seekBar = document.getElementById('seek-bar');
    const seekBarInner =  document.getElementById('seek-bar-inner');
    const textPosition = document.getElementById('seek-bar-text-position')
    const textDuration = document.getElementById('seek-bar-text-duration')

    const onMove = event => {
        audioElem.currentTime = ((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * audioElem.duration;
        event.preventDefault(); // Prevent accidental text selection
    };

    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    };

    seekBar.addEventListener('mousedown', event => {
        const newTime = ((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * audioElem.duration;
        audioElem.currentTime = newTime;

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

    const updateSeekBar = () => {
        // Save resources updating seek bar if it's not visible
        if (document.visibilityState != 'visible') {
            return;
        }

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

        textPosition.textContent = barCurrent;
        textDuration.textContent = barDuration;
        seekBarInner.style.width = barWidth
    }

    audioElem.addEventListener('durationchange', updateSeekBar);
    audioElem.addEventListener('timeupdate', updateSeekBar);

    // Seek bar is not updated when page is not visible. Immediately update it when the page does become visibile.
    document.addEventListener('visibilitychange', updateSeekBar);
});

// Play and pause buttons
document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();
    const pauseButton = document.getElementById('button-pause');
    const playButton = document.getElementById('button-play');

    // Play pause click actions
    pauseButton.addEventListener('click', () => audioElem.pause());
    playButton.addEventListener('click', () => audioElem.play());

    const updateButtons = () => {
        pauseButton.hidden = audioElem.paused;
        playButton.hidden = !audioElem.paused;
    };

    audioElem.addEventListener('pause', updateButtons);
    audioElem.addEventListener('play', updateButtons);

    // Hide pause button on initial page load, otherwise both play and pause will show
    pauseButton.hidden = true;
});

// Handle presence of buttons that perform file actions and are not available in offline mode
document.addEventListener('DOMContentLoaded', () => {
    const dislikeButton = document.getElementById('button-dislike');
    const copyButton = document.getElementById('button-copy');
    const shareButton = document.getElementById('button-share');
    const editButton = document.getElementById('button-edit');
    const deleteButton = document.getElementById('button-delete');

    const requiresRealTrack = [dislikeButton, copyButton, shareButton];
    const requiresWriteAccess = [editButton, deleteButton];

    if (!dislikeButton) {
        // if dislike button does not exist, we are running in offline mode and other buttons also don't exist
        return;
    }

    async function updateButtons() {
        const isRealTrack = queue.currentTrack && queue.currentTrack.track;
        for (const button of requiresRealTrack) {
            button.hidden = !isRealTrack;
        }

        const hasWriteAccess = isRealTrack && (await music.playlist(queue.currentTrack.track.playlistName)).write;
        for (const button of requiresWriteAccess) {
            button.hidden = !hasWriteAccess;
        }
    }

    updateButtons();
    eventBus.subscribe(MusicEvent.TRACK_CHANGE, updateButtons);
});
