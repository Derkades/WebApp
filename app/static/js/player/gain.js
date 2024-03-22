class Gain {
    /** @type {GainNode} */
    #gainNode;
    constructor() {
        document.addEventListener('DOMContentLoaded', () => {
            // Can only create AudioContext once media is playing
            getAudioElement().addEventListener('play', () => {
                console.debug('gain: create audio context');
                const audioContext = new AudioContext();
                const source = audioContext.createMediaElementSource(getAudioElement());
                this.#gainNode = audioContext.createGain();
                // Connect source to gain, and gain to output
                source.connect(this.#gainNode);
                this.#gainNode.connect(audioContext.destination);
            });
        })
    }

    setGain(gain) {
        if (this.#gainNode) {
            console.debug('gain: set to ', gain);
            this.#gainNode.gain.value = gain;
        } else {
            console.debug('gain: node not available yet');
            setTimeout(() => this.setGain(gain), 1000);
        }
    }
}

const gain = new Gain();

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('settings-audio-gain').addEventListener('input', event => {
        gain.setGain(event.target.value);
    });
});

eventBus.subscribe(MusicEvent.SETTINGS_LOADED, () => {
    gain.setGain(document.getElementById('settings-audio-gain').value);
});
