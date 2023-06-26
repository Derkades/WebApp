eventBus.subscribe(MusicEvent.PLAYBACK_CHANGE, () => {
    const audioElem = getAudioElement();

    navigator.mediaSession.playbackState = audioElem.paused ? 'paused' : 'playing';

    if (audioElem != null && isFinite(audioElem.duration) && isFinite(audioElem.currentTime) && isFinite(audioElem.playbackRate)) {
        navigator.mediaSession.setPositionState({
            duration: audioElem.duration,
            playbackRate: audioElem.playbackRate,
            position: audioElem.currentTime,
        });
    }
});

eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => {
    const track = queue.currentTrack.track();
    if (track === null) {
        console.warn('Not updating mediaSession, track info is null');
        return;
    }

    const metaObj = {
        // For some unknown reason this does not work everywhere. For example, it works on Chromium
        // mobile and desktop, but not the KDE media player widget with Firefox or Chromium.
        // Firefox mobile doesn't seem to support the MediaSession API at all.
        artwork: [{src: queue.currentTrack.imageBlobUrl}],
    }

    if (track.title && track.artists) {
        metaObj.title = track.title;
        metaObj.artist = track.artists.join(', ');
        if (track.album) {
            metaObj.album = track.album;
        }
    } else {
        metaObj.title = track.displayText();
    }

    navigator.mediaSession.metadata = new MediaMetadata(metaObj);
});

document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();

    // Media session events
    navigator.mediaSession.setActionHandler('play', () => {
        audioElem.play().then(() => eventBus.publish(MusicEvent.PLAYBACK_CHANGE));
    });
    navigator.mediaSession.setActionHandler('pause', () => {
        audioElem.pause();
        eventBus.publish(MusicEvent.PLAYBACK_CHANGE)
    });
    navigator.mediaSession.setActionHandler('seekto', callback => {
        audioElem.currentTime = callback.seekTime;
        eventBus.publish(MusicEvent.PLAYBACK_CHANGE)
    });
    navigator.mediaSession.setActionHandler('previoustrack', () => queue.previous());
    navigator.mediaSession.setActionHandler('nexttrack', () => queue.next());
});
