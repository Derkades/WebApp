class LastFM {
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

    init() {
        setInterval(() => this.update(), 1_000);
    };

    signalNewTrack() {
        const track = queue.currentTrack;

        if (this.currentlyPlayingTrack !== null && track.path == this.currentlyPlayingTrack.path) {
            console.debug('lastfm | still same track');
            return;
        }

        console.info('lastfm | track changed');
        this.currentlyPlayingTrack = track;
        this.hasScrobbled = false;
        this.playingCounter = 0;
        // last.fm requires track to be played for half its duration or for 4 minutes (whichever is less)
        this.requiredPlayingCounter = Math.min(4*60, Math.round(track.duration / 2));
        this.startTimestamp = Math.floor((new Date()).getTime() / 1000);
    }

    async update() {
        if (this.currentlyPlayingTrack === null) {
            console.debug('lastfm | no current track');
            return;
        }

        const audioElem = getAudioElement();
        if (audioElem === null) {
            console.warn('lastfm | no audio element');
            return;
        }

        if (audioElem.paused) {
            console.debug('lastfm | audio element paused');
            return;
        }

        this.playingCounter++;

        console.debug('lastfm | playing, counter:', this.playingCounter, '/', this.requiredPlayingCounter);

        // Send 'Now playing' after 10 seconds, then every 3 minutes
        if (this.playingCounter % (3*60) === 10) {
            console.info('lastfm | update now playing');
            await this.updateNowPlaying();
        }

        if (!this.hasScrobbled && this.playingCounter > this.requiredPlayingCounter) {
            console.info('lastfm | scrobble');
            this.hasScrobbled = true;
            await this.scrobble();
        }
    }

    async updateNowPlaying() {
        await jsonPost('/lastfm_now_playing', {track: this.currentlyPlayingTrack.path});
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

const lastfm = new LastFM();
