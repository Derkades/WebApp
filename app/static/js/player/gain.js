class Gain {
    /** @type {GainNode} */
    #gainNode;
    constructor() {
        const audioContext = new AudioContext();
        const source = audioContext.createMediaElementSource(getAudioElement());
        this.#gainNode = audioContext.createGain();
        // Connect source to gain, and gain to output
        source.connect(this.#gainNode);
        this.#gainNode.connect(audioContext.destination);
    }

    setGain(gain) {
        console.debug('set gain to ', gain);
        this.#gainNode.gain.value = gain;
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
