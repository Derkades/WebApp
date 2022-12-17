class LastFM {
    init() {
        setInterval(() => this.updateNowPlaying(), 30_000);
    };

    updateNowPlaying() {
        const audioElem = getAudioElement();
        if (audioElem === null) {
            return;
        }

        if (audioElem.paused) {
            return;
        }

        const track = queue.currentTrack;

        if (track.duration < 60) {
            return;
        }

        jsonPost('/lastfm_now_playing', {track: track.path});
    };
}

const lastfm = new LastFM();
