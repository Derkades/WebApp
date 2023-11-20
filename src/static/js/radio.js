
const updateInterval = 2000;
setInterval(update, updateInterval);
setInterval(updateNext, 10_000);

const state = {
    currentTrack: null,
    nextTrack: null,
}

async function update() {
    const currentResponse = await fetch('/radio/current');
    const currentJson = await currentResponse.json();

    if (state.currentTrack === null || state.currentTrack.path != currentJson.path) {
        state.currentTrack = currentJson;
        document.getElementById('status').textContent = 'loading...';
        console.info('replace audio elem');
        replaceAudioElem();
        return;
    }

    const audioElem = document.getElementById('audio').childNodes[0];

    if (audioElem === null) {
        console.debug('audio elem null');
        document.getElementById('status').textContent = 'audio null';
        return;
    }

    document.getElementById('current').innerText = currentJson.path;
    const timezoneOffset = new Date().getTimezoneOffset() * 60 * 1000;
    const currentPos = (Date.now() - currentJson.start_time) + timezoneOffset;
    const offset = audioElem.currentTime*1000 - currentPos;

    if (Math.abs(offset) > 1000) {
        console.debug('large offset', offset, 'skip from', audioElem.currentTime, 'to', currentPos / 1000);
        audioElem.currentTime = currentPos / 1000;
        audioElem.playbackRate = 1;
        document.getElementById('status').textContent = 'very out of sync';
    } else {
        const rate = 1 - offset / (10*updateInterval);
        console.debug('small offset', offset, 'rate', rate);
        audioElem.playbackRate = rate;
        if (Math.abs(offset) < 50) {
            document.getElementById('status').textContent = 'in sync: ' + Math.floor(offset) + 'ms';
        } else {
            document.getElementById('status').textContent = 'out of sync: ' + Math.floor(offset) + 'ms';
        }
    }
};

async function updateNext() {
    const nextResponse = await fetch('/radio/next');
    const nextJson = await nextResponse.json();
    document.getElementById('next').textContent = nextJson.path;
};

async function replaceAudioElem() {
    const audioElem = document.createElement('audio');
    console.log('replace children');
    const sourceElem = document.createElement('source');
    sourceElem.src = '/get_track?path=' + encodeURIComponent(state.currentTrack.path) + '&type=webm_opus_high';
    audioElem.appendChild(sourceElem);
    audioElem.controls = true;
    audioElem.play();

    document.getElementById('audio').replaceChildren(audioElem);
};
