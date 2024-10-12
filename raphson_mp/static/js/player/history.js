const PLAYED_TIMER_INTERVAL_SECONDS = 5;

class History {
    /** @type {boolean} */
    hasScrobbled;
    /** @type {number} */
    playCounter;
    /** @type {number} */
    requiredPlayingCounter;
    /** @type {number} */
    startTimestamp;

    constructor() {
        eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => this.#onNewTrack());
    }

    #onNewTrack() {
        this.hasScrobbled = false;
        this.playingCounter = 0;
        this.startTimestamp = Math.floor((new Date()).getTime() / 1000);
        // last.fm requires track to be played for half its duration or for 4 minutes (whichever is less)
        if (queue.currentTrack && queue.currentTrack.track) {
            this.requiredPlayingCounter = Math.min(4*60, Math.round(queue.currentTrack.track.duration / 2));
        } else {
            this.requiredPlayingCounter = null;
        }
    }

    async update() {
        if (this.requiredPlayingCounter == null) {
            console.debug('history: no current track');
            return;
        }

        const audioElem = getAudioElement();

        if (audioElem.paused) {
            console.debug('history: audio element paused');
            return;
        }

        this.playingCounter += PLAYED_TIMER_INTERVAL_SECONDS;

        console.debug('history: playing, counter:', this.playingCounter, '/', this.requiredPlayingCounter);

        if (!this.hasScrobbled && this.playingCounter > this.requiredPlayingCounter) {
            console.info('history: played');
            this.hasScrobbled = true;
            await music.played(queue.currentTrack.track, this.startTimestamp);
        }
    }

    async updateNowPlaying() {
        if (this.requiredPlayingCounter == null) {
            console.debug('history: no track playing or not an actual track');
            return;
        }
        const audioElem = getAudioElement();
        await music.nowPlaying(queue.currentTrack.track , audioElem.paused, audioElem.currentTime);
    }

}

const history = new History();
let nowPlayingTimerId = null;

function startNowPlayingTimer(interval) {
    if (nowPlayingTimerId != null) {
        clearInterval(nowPlayingTimerId);
    }
    nowPlayingTimerId = setInterval(() => history.updateNowPlaying(), interval);
    history.updateNowPlaying(); // Also update immediately
}

document.addEventListener('DOMContentLoaded', () => {
    setInterval(() => history.update(), PLAYED_TIMER_INTERVAL_SECONDS * 1000);

    // When paused, update immediately, then every minute
    getAudioElement().addEventListener('pause', () => startNowPlayingTimer(60_000));
    // When resumed, update immediately, then every minute
    getAudioElement().addEventListener('play', () => startNowPlayingTimer(10_000));
    // When modifying the interval, also modify route_data() in routes/activity.py
});
