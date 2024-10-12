class MediaSessionUpdater {
    constructor() {
        document.addEventListener('DOMContentLoaded', () => {
            const audioElem = getAudioElement();

            eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => {
                this.updateMetadata();
            });

            // Media session events
            navigator.mediaSession.setActionHandler('play', () => {
                audioElem.play();
            });
            navigator.mediaSession.setActionHandler('pause', () => {
                audioElem.pause();
            });
            navigator.mediaSession.setActionHandler('seekto', callback => {
                audioElem.currentTime = callback.seekTime;
            });
            navigator.mediaSession.setActionHandler('previoustrack', () => queue.previous());
            navigator.mediaSession.setActionHandler('nexttrack', () => queue.next());
        });
    }

    updateState() {
        const audioElem = getAudioElement();
        navigator.mediaSession.playbackState = audioElem.paused ? 'paused' : 'playing';
    }

    updatePosition() {
        const audioElem = getAudioElement();

        if (audioElem == null || !isFinite(audioElem.currentTime) || !isFinite(audioElem.playbackRate) || !isFinite(audioElem.duration)) {
            console.debug('mediasession: skip update, invalid value');
            return;
        }

        const positionState = {
            duration: audioElem.duration,
            playbackRate: audioElem.playbackRate,
            position: audioElem.currentTime,
        }
        console.debug('mediasession: do update', positionState);
        navigator.mediaSession.setPositionState(positionState);
    }

    updateMetadata() {
        const track = queue.currentTrack.track;
        if (track === null) {
            console.warn('mediasession: track info is null');
            navigator.mediaSession.metadata = null;
            return;
        }

        const metaObj = {
            // For some unknown reason this does not work everywhere. For example, it works on Chromium
            // mobile and desktop, but not the KDE media player widget with Firefox or Chromium.
            // Firefox mobile doesn't seem to support the MediaSession API at all.
            artwork: [{src: queue.currentTrack.imageUrl}],
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

        console.debug('mediasession: set metadata', metaObj);
        navigator.mediaSession.metadata = new MediaMetadata(metaObj);
    }
}

const mediaSessionUpdater = new MediaSessionUpdater();
