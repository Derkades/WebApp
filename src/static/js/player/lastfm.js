class LastFM {
    currentlyPlayingTrackPath;
    hasScrobbled;
    playCounter;
    requiredPlayingCounter;
    startTimestamp;

    constructor() {
        this.currentlyPlayingTrackPath = null;
    }

    init() {
        setInterval(() => this.update(), 1_000);
    };

    signalNewTrack() {
        const track = queue.currentTrack;

        if (track.path == this.currentlyPlayingTrackPath) {
            console.debug('lastfm | still same track');
            return;
        }

        // last.fm requires track to be at least 30 seconds, and played for
        // half its duration or for 4 minutes (whichever is less)

        // We use a longer minimum duration of 2 minutes to be sure non-music
        // audio (like memes) is skipped
        if (track.duration > 120) {
            console.info('lastfm | track changed');
            this.currentlyPlayingTrackPath = track.path;
            this.hasScrobbled = false;
            this.playingCounter = 0;
            this.requiredPlayingCounter = Math.min(4*60, Math.round(track.duration / 2));
            this.startTimestamp = Math.floor((new Date()).getTime() / 1000);
        } else {
            console.info('lastfm | track changed, not eligible for scrobbling');
            this.currentlyPlayingTrackPath = null;
        }
    }

    async update() {
        if (this.currentlyPlayingTrackPath === null) {
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

        console.debug('lastfm | playing, counter:', this.playingCounter)

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
        await jsonPost('/lastfm_now_playing', {track: this.currentlyPlayingTrackPath});
    }

    async scrobble() {
        await jsonPost('/lastfm_scrobble', {track: this.currentlyPlayingTrackPath, start_timestamp: this.startTimestamp});
    }
}

const lastfm = new LastFM();
