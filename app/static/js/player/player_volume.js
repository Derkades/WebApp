function getTransformedVolume(volumeZeroToHundred) {
    // https://www.dr-lex.be/info-stuff/volumecontrols.html
    // Values for 60dB dynamic range
    const a = 1e-3
    const b = 6.907 // slightly lower than value in article so result never exceeds 1.0
    const x = volumeZeroToHundred / 100;
    return a * Math.exp(x * b);
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

    const audioElem = getAudioElement();
    audioElem.volume = getTransformedVolume(volume);
}

document.addEventListener('DOMContentLoaded', () => {
    // Respond to volume button changes
    document.getElementById('settings-volume').addEventListener('input', () => onVolumeChange());

    // Scroll to change volume
    const volume = document.getElementById('settings-volume');
    volume.addEventListener('wheel', event => {
        volume.value = parseInt(volume.value) + (event.deltaY < 0 ? 2 : -2);
        onVolumeChange();
    }, {passive: true});
})
