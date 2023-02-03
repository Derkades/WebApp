document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();

    // Skip to previous
    document.getElementById('button-prev').addEventListener('click', () => {
        // Try to skip to beginning of current track first
        if (audioElem.currentTime > 15 || this.previousTracks.length == 0) {
            audioElem.currentTime = 0;
            onPlaybackStateChange();
            return;
        }

        queue.previous();
    });

    // Skip to next
    document.getElementById('button-next').addEventListener('click', () => queue.next());

    // Play pause
    document.getElementById('button-play').addEventListener('click', () => {
        audioElem.play().then(onPlaybackStateChange());
    });
    document.getElementById('button-pause').addEventListener('click', () => {
        audioElem.pause();
        onPlaybackStateChange();
    });

    // Seek bar
    const seekBar = document.getElementById('outer-progress-bar');

    const onMove = event => {
        audioElem.currentTime = ((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * audioElem.duration;
        onPlaybackStateChange();
        event.preventDefault(); // Prevent accidental text selection
    };

    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    };

    seekBar.addEventListener('mousedown', event => {
        audioElem.currentTime = ((event.clientX - seekBar.offsetLeft) / seekBar.offsetWidth) * audioElem.duration;
        onPlaybackStateChange();

        // Keep updating while mouse is moving
        document.addEventListener('mousemove', onMove);

        // Unregister events on mouseup event
        document.addEventListener('mouseup', onUp);

        event.preventDefault(); // Prevent accidental text selection
    });
});
