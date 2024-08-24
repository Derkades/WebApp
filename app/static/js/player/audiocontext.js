class AudioContextManager {
    fftSize = 2**13;
    /** @type {AudioContext} */
    #audioContext;
    /** @type {GainNode} */
    #gainNode = null;
    /** @type {GainNode} */
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
                if (this.#gainValue) { // Gain was set while audio was still paused
                    this.#gainNode.gain.value = this.#gainValue;
                }
                source.connect(this.analyser);
                source.connect(this.#gainNode);
                this.#gainNode.connect(this.#audioContext.destination);
            });
        });
    }

    setGain(gain) {
        // If gain node is available, we can immediately set the gain
        // Otherwise, we only set the value and the 'play' event listener will set the gain

        if (this.#gainNode) {
            this.#gainNode.gain.value = gain;
        } else {
            this.#gainValue = gain;

        }
    }
}

const audioContextManager = new AudioContextManager();

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('settings-audio-gain').addEventListener('input', event => {
        audioContextManager.setGain(event.target.value);
    });
});

eventBus.subscribe(MusicEvent.SETTINGS_LOADED, () => {
    audioContextManager.setGain(document.getElementById('settings-audio-gain').value);
});
