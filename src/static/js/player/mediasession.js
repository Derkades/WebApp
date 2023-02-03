function updateMediaSessionState() {
    const audioElem = getAudioElement();

    navigator.mediaSession.playbackState = audioElem.paused ? 'paused' : 'playing';

    if (audioElem != null && isFinite(audioElem.duration) && isFinite(audioElem.currentTime) && isFinite(audioElem.playbackRate)) {
        navigator.mediaSession.setPositionState({
            duration: audioElem.duration,
            playbackRate: audioElem.playbackRate,
            position: audioElem.currentTime,
        });
    }
}

function updateMediaSessionTrack() {
    const track = queue.currentTrack.track();
    if (track === null) {
        console.warn('Not updating mediaSession, track info is null');
        return;
    }

    navigator.mediaSession.metadata = new MediaMetadata({
        title: track.title !== null ? track.title : track.display,
        album: track.album !== null ? track.album : 'Unknown Album',
        artist: track.artists !== null ? track.artists.join(' & ') : 'Unknown Artist',
        // For some unknown reason this does not work everywhere. For example, it works on Chromium
        // mobile and desktop, but not the KDE media player widget with Firefox or Chromium.
        // Firefox mobile doesn't seem to support the MediaSession API at all.
        artwork: [{src: queue.currentTrack.imageBlobUrl}],
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();

    // Media session events
    navigator.mediaSession.setActionHandler('play', () => {
        audioElem.play().then(onPlaybackStateChange);
    });
    navigator.mediaSession.setActionHandler('pause', () => {
        audioElem.pause();
        onPlaybackStateChange();
    });
    navigator.mediaSession.setActionHandler('seekto', callback => {
        audioElem.currentTime = callback.seekTime;
        onPlaybackStateChange();
    });
    navigator.mediaSession.setActionHandler('previoustrack', () => queue.previous());
    navigator.mediaSession.setActionHandler('nexttrack', () => queue.next());
});
