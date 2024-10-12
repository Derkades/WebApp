class AudioContextManager {
    fftSize = 2**13;
    /** @type {AudioContext} */
    #audioContext;
    /** @type {GainNode} */
    #gainNode = null;
    /** @type {number} */
    #gainValue = null;
    /** @type {AnalyserNode} */
    analyser = null;

    constructor() {
        document.addEventListener('DOMContentLoaded', () => {
            // Can only create AudioContext once media is playing
            getAudioElement().addEventListener('play', () => {
                if (this.#audioContext) {
                    return;
                }
                console.debug('autocontext: create');
                this.#audioContext = new AudioContext();
                const source = this.#audioContext.createMediaElementSource(getAudioElement());
                this.analyser = this.#audioContext.createAnalyser(); // used by visualiser
                this.analyser.fftSize = this.fftSize;
                this.#gainNode = this.#audioContext.createGain();
                this.applyGain(); // If gain was set while audio was still paused
                source.connect(this.analyser);
                source.connect(this.#gainNode);
                this.#gainNode.connect(this.#audioContext.destination);
            });
        });
    }

    applyGain() {
        // If gain node is available, we can immediately set the gain
        // Otherwise, the 'play' event listener will call this method again
        if (!this.#gainNode) {
            console.debug('autocontext: gainNode not available yet');
            return;
        }
        const gain = this.#gainValue ? this.#gainValue : 1;
        const volume = getTransformedVolume(document.getElementById('settings-volume').value);
        console.debug('audiocontext: set gain:', gain, volume, gain * volume);
        // exponential function cannot handle 0 value, so clamp to tiny minimum value instead
        this.#gainNode.gain.exponentialRampToValueAtTime(Math.max(gain * volume, 0.0001), this.#audioContext.currentTime + 0.1);
    }

    setGain(gain) {
        this.#gainValue = gain;
        this.applyGain();
    }
}

const audioContextManager = new AudioContextManager();

function getTransformedVolume(volumeZeroToHundred) {
    // https://www.dr-lex.be/info-stuff/volumecontrols.html
    return Math.pow(volumeZeroToHundred / 100, 3);
}

function onVolumeChange() {
    const slider = document.getElementById('settings-volume');
    const volume = slider.value;

    slider.classList.remove('input-volume-high', 'input-volume-medium', 'input-volume-low');
    if (volume > 60) {
        slider.classList.add('input-volume-high');
    } else if (volume > 30) {
        slider.classList.add('input-volume-medium');
    } else {
        slider.classList.add('input-volume-low');
    }

    audioContextManager.applyGain();
}

document.addEventListener('DOMContentLoaded', () => {
    // Respond to gain changes
    document.getElementById('settings-audio-gain').addEventListener('input', event => {
        audioContextManager.setGain(event.target.value);
    });

    // Respond to volume button changes
    document.getElementById('settings-volume').addEventListener('input', () => onVolumeChange());

    // Scroll to change volume
    const volume = document.getElementById('settings-volume');
    volume.addEventListener('wheel', event => {
        volume.value = parseInt(volume.value) + (event.deltaY < 0 ? 2 : -2);
        onVolumeChange();
    }, {passive: true});

    // Audio element should always be playing at max volume
    // Volume is set using GainNode
    getAudioElement().volume = 1;
});

eventBus.subscribe(MusicEvent.SETTINGS_LOADED, () => {
    audioContextManager.setGain(document.getElementById('settings-audio-gain').value);
    onVolumeChange();
});
