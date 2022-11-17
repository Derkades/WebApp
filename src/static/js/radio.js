setInterval(update, 2000);

const minTimeCorrection = 0.5;

const state = {
    currentTrack: null,
    nextTrack: null,
    audioElemNeedsChange: false,
}

async function update() {
    const currentResponse = await fetch('/radio_current');
    const currentJson = await currentResponse.json();
    document.getElementById('current').innerText = currentJson.path;
    const currentPos = Date.now() / 1000 - currentJson.start_time;
    document.getElementById('current-pos').innerText = currentPos;
    if (state.currentTrack === null || state.currentTrack.path != currentJson.path) {
        state.currentTrack = currentJson;
        state.audioElemNeedsChange = true;
    }

    const nextResponse = await fetch('/radio_next');
    const nextJson = await nextResponse.json();
    document.getElementById('next').textContent = nextJson.path;
    document.getElementById('next-start').textContent = nextJson.start_time;

    const audioElem = document.getElementById('audio').childNodes[0];
    if (audioElem !== undefined) {
        if (Math.abs(audioElem.currentTime - currentPos) > minTimeCorrection) {
            console.log('time correction', audioElem.currentTime, currentPos);
            audioElem.currentTime = currentPos + minTimeCorrection / 2;
        }
        audioElem.play();
    }

    replaceAudioElem();
};

async function replaceAudioElem() {
    if (!state.audioElemNeedsChange) {
        return;
    }

    state.audioElemNeedsChange = false;

    const audioElem = document.createElement('audio');
    console.log('replace children');
    const csrf = document.getElementById('csrf').textContent;
    const sourceElem = document.createElement('source');
    sourceElem.src = '/get_track?path=' + encodeURIComponent(state.currentTrack.path) + '&csrf=' + csrf;
    audioElem.appendChild(sourceElem);
    audioElem.controls = true;

    document.getElementById('audio').replaceChildren(audioElem);
};
