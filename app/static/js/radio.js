"use strict";

const updateInterval = 1000;

class RadioTrack {
    /** @type {number} */
    startTime;
    /** @type {DownloadedTrack} */
    downloadedTrack;
    constructor(startTime, downloadedTrack) {
        this.startTime = startTime;
        this.downloadedTrack = downloadedTrack;
    }
}

const state = {
    /** @type {RadioTrack} */
    currentTrack: null,
    /** @type {RadioTrack} */
    nextTrack: null,
}

async function updateState() {
    navigator.locks.request('update_radio_state', async () => {
        if (state.currentTrack && state.nextTrack) {
            console.debug('updateState: ok');
            return;
        }

        const json = await jsonGet('/radio/info');

        if (state.currentTrack == null) {
            console.debug('updateState: init currentTrack');
            const download = await new Track(json.current).download();
            state.currentTrack = new RadioTrack(json.current_time, download);
        }

        if (state.nextTrack == null) {
            console.debug('updateState: init nextTrack');
            const download = await new Track(json.next).download();
            state.nextTrack = new RadioTrack(json.next_time, download);
        }
    });
}

setInterval(updateState, 10_000);
updateState();

document.addEventListener('DOMContentLoaded', () => {
    /** @type {HTMLAudioElement} */
    const audio = document.getElementById('audio');
    /** @type {HTMLImageElement} */
    const image = document.getElementById('image');
    /** @type {HTMLSpanElement} */
    const current = document.getElementById('current');
    /** @type {HTMLSpanElement} */
    const next = document.getElementById('next');
    /** @type {HTMLSpanElement} */
    const status = document.getElementById('status');
    /** @type {HTMLButtonElement} */
    const play = document.getElementById('play');

    async function setSrc() {
        console.debug('setSrc');
        audio.src = state.currentTrack.downloadedTrack.audioUrl;
        image.src = state.currentTrack.downloadedTrack.imageUrl;

        try {
            await audio.play();
        } catch (err) {
            console.warn('cannot play, autoplay blocked?', err);
        }
    }

    async function update() {
        if (state.currentTrack != null) {
            current.textContent = state.currentTrack.downloadedTrack.track.displayText(true, true);
        } else {
            current.textContent = 'loading';
        }

        if (state.nextTrack != null) {
            next.textContent = state.nextTrack.downloadedTrack.track.displayText(true, true);
        } else {
            next.textContent = 'loading';
        }

        if (state.currentTrack == null) {
            return;
        }

        // load initial track, once available
        if (audio.src == '') {
            console.debug('set initial audio');
            await setSrc();
        }

        const timezoneOffset = new Date().getTimezoneOffset() * 60 * 1000;
        const currentPos = (Date.now() - state.currentTrack.startTime) + timezoneOffset;
        const offset = audio.currentTime*1000 - currentPos;
        let rate = 1;

        if (Math.abs(offset) > 1000) {
            console.debug('large offset', offset, 'skip from', audio.currentTime, 'to', currentPos / 1000);
            audio.currentTime = currentPos / 1000;
            audio.playbackRate = 1;
            status.textContent = 'very out of sync';
        } else {
            // Aim to be in sync in 60 seconds
            rate = 1 - offset / (60*updateInterval);
            audio.playbackRate = rate;
            if (Math.abs(offset) < 50) {
                status.textContent = 'in sync';
            } else {
                status.textContent = 'out of sync';
            }
        }

        status.textContent += " | " + Math.floor(offset) + 'ms';
        status.textContent += " | " + Math.round(rate * 1000) / 1000 + 'x';
    };

    setInterval(update, updateInterval);

    audio.addEventListener('ended', async () => {
        state.currentTrack = state.nextTrack;
        state.nextTrack = null;
        await setSrc();
    });

    play.addEventListener('click', () => {
        audio.play();
    })
});
