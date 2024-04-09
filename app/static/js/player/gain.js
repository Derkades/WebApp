class Gain {
    setGain(gain) {
        const gainNode = audioContextManager.gain;
        if (gainNode) {
            console.debug('gain: set to ', gain);
            gainNode.gain.value = gain;
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
