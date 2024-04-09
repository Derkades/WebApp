class MediaSessionUpdater {
    /** @type {number} */
    lastPositionUpdate = 0;
    constructor() {
        document.addEventListener('DOMContentLoaded', () => {
            const audioElem = getAudioElement();

            audioElem.addEventListener('timeupdate', () => this.updatePosition());
            audioElem.addEventListener('durationchange', () => this.updatePosition());

            eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => this.updateMetadata());

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

    updatePosition() {
        const now = Date.now();
        if (now - this.lastPositionUpdate < 1000) {
            console.debug('mediasession: skip update');
            return;
        }
        this.lastPositionUpdate = now;

        const audioElem = getAudioElement();

        navigator.mediaSession.playbackState = audioElem.paused ? 'paused' : 'playing';

        if (audioElem == null || !isFinite(audioElem.currentTime) || !isFinite(audioElem.playbackRate) || !isFinite(audioElem.duration)) {
            console.debug('mediasession: skip update, invalid value');
            return;
        }

        console.debug('mediasession: do update');

        navigator.mediaSession.setPositionState({
            duration: audioElem.duration,
            playbackRate: audioElem.playbackRate,
            position: audioElem.currentTime,
        });
    }

    updateMetadata() {
        const track = queue.currentTrack.track();
        if (track === null) {
            console.warn('mediasession: skip update, track info is null');
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
    }
}

const mediaSessionUpdater = new MediaSessionUpdater();
