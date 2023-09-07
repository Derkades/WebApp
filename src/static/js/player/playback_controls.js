document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();

    // Skip to previous
    document.getElementById('button-prev').addEventListener('click', () => {
        // Try to skip to beginning of current track first
        if (audioElem.currentTime > 15 || queue.previousTracks.length == 0) {
            audioElem.currentTime = 0;
            eventBus.publish(MusicEvent.PLAYBACK_CHANGE)
            return;
        }

        queue.previous();
    });

    // Skip to next
    document.getElementById('button-next').addEventListener('click', () => queue.next());

    // Play pause
    document.getElementById('button-play').addEventListener('click', () => {
        audioElem.play().then(() => eventBus.publish(MusicEvent.PLAYBACK_CHANGE));
    });
    document.getElementById('button-pause').addEventListener('click', () => {
        audioElem.pause();
        eventBus.publish(MusicEvent.PLAYBACK_CHANGE)
    });

    // Seek bar
    const seekBar = document.getElementById('outer-progress-bar');

    const onMove = event => {
        if (!history.currentlyPlayingTrack) {
            return;
        }

        audioElem.currentTime = ((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * history.currentlyPlayingTrack.duration;
        eventBus.publish(MusicEvent.PLAYBACK_CHANGE)
        event.preventDefault(); // Prevent accidental text selection
    };

    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    };

    seekBar.addEventListener('mousedown', event => {
        if (!history.currentlyPlayingTrack) {
            return;
        }

        seekAbsolute(((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * history.currentlyPlayingTrack.duration);

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

    const volume = document.getElementById('settings-volume');
    volume.addEventListener('wheel', event => {
        volume.value = parseInt(volume.value) + (event.deltaY < 0 ? 2 : -2);
        onVolumeChange();
    }, {passive: true});
});

// Update seek bar
eventBus.subscribe(MusicEvent.PLAYBACK_CHANGE, () => {
    const audioElem = getAudioElement();

    var barCurrent;
    var barDuration;
    var barWidth;

    if (history.currentlyPlayingTrack && isFinite(audioElem.currentTime)) {
        barCurrent = secondsToString(Math.round(audioElem.currentTime));
        barDuration = secondsToString(Math.round(history.currentlyPlayingTrack.duration));
        barWidth = ((audioElem.currentTime / history.currentlyPlayingTrack.duration) * 100) + '%';
    } else {
        barCurrent = '--:--';
        barDuration = '--:--';
        barWidth = 0;
    }

    document.getElementById('progress-time-current').innerText = barCurrent;
    document.getElementById('progress-time-duration').innerText = barDuration;
    document.getElementById('progress-bar').style.width = barWidth
});

// Update play/pause buttons
eventBus.subscribe(MusicEvent.PLAYBACK_CHANGE, () => {
    if (getAudioElement().paused) {
        document.getElementById('button-pause').classList.add('hidden');
        document.getElementById('button-play').classList.remove('hidden');
    } else {
        document.getElementById('button-pause').classList.remove('hidden');
        document.getElementById('button-play').classList.add('hidden');
    }
});

// Only show metadata edit and track delete buttons if playlist is writable
eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => {
    const track = queue.currentTrack.track();

    if (track !== null && track.playlist().write) {
        document.getElementById('button-edit').classList.remove('hidden');
        document.getElementById('button-delete-track').classList.remove('hidden');
    } else {
        document.getElementById('button-edit').classList.add('hidden');
        document.getElementById('button-delete-track').classList.add('hidden');
    }
});
