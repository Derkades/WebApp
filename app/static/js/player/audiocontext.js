class AudioContextManager {
    /** @type {AudioContext} */
    #audioContext;
    /** @type {GainNode} */
    gain = null;
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
                this.analyser = this.#audioContext.createAnalyser();
                this.gain = this.#audioContext.createGain();
                source.connect(this.analyser);
                source.connect(this.gain);
                this.gain.connect(this.#audioContext.destination)
                source.connect(this.#audioContext.destination);
            });
        });
    }
}

const audioContextManager = new AudioContextManager();
