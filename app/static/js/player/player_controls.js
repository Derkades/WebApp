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
        const audioElem = getAudioElement();
        audioElem.currentTime = ((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * audioElem.duration;
        eventBus.publish(MusicEvent.PLAYBACK_CHANGE)
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

    // Hide buttons initially
    document.getElementById('button-edit').classList.add('hidden');
    document.getElementById('button-delete').classList.add('hidden');
    document.getElementById('button-dislike').classList.add('hidden');
});

// Update seek bar
eventBus.subscribe(MusicEvent.PLAYBACK_CHANGE, () => {
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

    if (track !== null) {
        document.getElementById('button-dislike').classList.remove('hidden'); // Not available for virtual news tracks
        if (track.playlist().write) {
            // Only available with write access
            document.getElementById('button-edit').classList.remove('hidden');
            document.getElementById('button-delete').classList.remove('hidden');
        }
    } else {
        document.getElementById('button-edit').classList.add('hidden');
        document.getElementById('button-delete').classList.add('hidden');
        document.getElementById('button-dislike').classList.add('hidden');
    }
});
