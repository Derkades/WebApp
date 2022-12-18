
const updateInterval = 2000;
setInterval(update, updateInterval);
setInterval(updateNext, 10_000);

const state = {
    currentTrack: null,
    nextTrack: null,
}

async function update() {
    const currentResponse = await fetch('/radio_current');
    const currentJson = await currentResponse.json();

    if (state.currentTrack === null || state.currentTrack.path != currentJson.path) {
        state.currentTrack = currentJson;
        console.info('replace audio elem')
        replaceAudioElem();
        return;
    }

    const audioElem = document.getElementById('audio').childNodes[0];

    if (audioElem === null) {
        console.debug('audio elem null');
        return;
    }

    document.getElementById('current').innerText = currentJson.path;
    const timezoneOffset = new Date().getTimezoneOffset() * 60 * 1000;
    const currentPos = (Date.now() - currentJson.start_time) + timezoneOffset;
    const offset = audioElem.currentTime*1000 - currentPos;
    document.getElementById('current-pos').innerText = currentPos;

    if (Math.abs(offset) > 1000) {
        console.debug('large offset', offset, 'skip from', audioElem.currentTime, 'to', currentPos / 1000);
        audioElem.currentTime = currentPos / 1000;
        audioElem.playbackRate = 1;
    } else {
        const rate = 1 - offset / (10*updateInterval);
        console.debug('small offset', offset, 'rate', rate);
        audioElem.playbackRate = rate;
    }
};

async function updateNext() {
    const nextResponse = await fetch('/radio_next');
    const nextJson = await nextResponse.json();
    document.getElementById('next').textContent = nextJson.path;
    document.getElementById('next-start').textContent = nextJson.start_time;
};

async function replaceAudioElem() {
    const audioElem = document.createElement('audio');
    console.log('replace children');
    const csrf = document.getElementById('csrf').textContent;
    const sourceElem = document.createElement('source');
    sourceElem.src = '/get_track?path=' + encodeURIComponent(state.currentTrack.path) + '&csrf=' + csrf;
    audioElem.appendChild(sourceElem);
    audioElem.controls = true;
    audioElem.play();

    document.getElementById('audio').replaceChildren(audioElem);
};
