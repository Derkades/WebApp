class History {
    /** @type {Track} */
    currentlyPlayingTrack;
    /** @type {boolean} */
    hasScrobbled;
    /** @type {number} */
    playCounter;
    /** @type {number} */
    requiredPlayingCounter;
    /** @type {number} */
    startTimestamp;

    constructor() {
        this.currentlyPlayingTrack = null;
    }

    signalNewTrack() {
        const track = queue.currentTrack.track();
        if (track === null) {
            console.warn('history | missing track info');
            this.currentlyPlayingTrack = false;
            return;
        }
        console.info('history | track changed');
        this.currentlyPlayingTrack = track;
        this.hasScrobbled = false;
        this.playingCounter = 0;
        // last.fm requires track to be played for half its duration or for 4 minutes (whichever is less)
        this.requiredPlayingCounter = Math.min(4*60, Math.round(track.duration / 2));
        this.startTimestamp = Math.floor((new Date()).getTime() / 1000);
    }

    async update() {
        if (this.currentlyPlayingTrack === null) {
            console.debug('history | no current track');
            return;
        }

        const audioElem = getAudioElement();
        if (audioElem === null) {
            console.warn('history | no audio element');
            return;
        }

        if (audioElem.paused) {
            console.debug('history | audio element paused');
            return;
        }

        this.playingCounter++;

        console.debug('history | playing, counter:', this.playingCounter, '/', this.requiredPlayingCounter);

        // Send 'Now playing' after 5 seconds, then every minute
        // If you modify this, also modify history() in app.py
        if (this.playingCounter % (60) === 5) {
            console.info('history | update now playing');
            await this.updateNowPlaying();
        }

        if (!this.hasScrobbled && this.playingCounter > this.requiredPlayingCounter) {
            console.info('history | played');
            this.hasScrobbled = true;
            await this.scrobble();
        }
    }

    async updateNowPlaying() {
        await jsonPost('/now_playing', {track: this.currentlyPlayingTrack.path});
    }

    async scrobble() {
        const data = {
            track: this.currentlyPlayingTrack.path,
            playlist: this.currentlyPlayingTrack.playlistPath,
            startTimestamp: this.startTimestamp,
            lastfmEligible: this.currentlyPlayingTrack.duration > 30, // last.fm requires track to be at least 30 seconds
        }
        await jsonPost('/history_played', data);
    }
}

const history = new History();

document.addEventListener('DOMContentLoaded', () => {
    setInterval(() => history.update(), 1_000);
});
