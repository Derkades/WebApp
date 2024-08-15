class CachedTrack {
    track;
    audioBlobUrl;
    imageBlobUrl;
    constructor(track, audioBlobUrl, imageBlobUrl) {
        this.track = track;
        this.audioBlobUrl = audioBlobUrl;
        this.imageBlobUrl = imageBlobUrl;
    }
}

const tracks = [];
const cachedTracks = [];

async function downloadRandomTrack() {
    const track = choice(tracks);
    console.info('downloading:', track.path);
    const encodedPath = encodeURIComponent(track.path);

    const imageResponse = await fetch(`/track/album_cover?path=${encodedPath}&quality=high`);
    const imageBlob = await imageResponse.blob();

    const audioResponse = await fetch(`/track/audio?path=${encodedPath}&type=webm_opus_high`);
    const audioBlob = await audioResponse.blob();
    console.info('done downloading:', track.path);
    return new CachedTrack(track, URL.createObjectURL(audioBlob), URL.createObjectURL(imageBlob));
}

async function fillCachedTracks() {
    if (cachedTracks.length > 3) {
        return;
    }

    const cachedTrack = await downloadRandomTrack();
    for (const cachedTrack2 of cachedTracks) {
        if (cachedTrack.track.path == cachedTrack2.track.path) {
            console.warn('track is already in queue, skipping');
            return;
        }
    }
    cachedTracks.push(cachedTrack);

    fillCachedTracks();
}

document.addEventListener('DOMContentLoaded', () => {
    /**
     * @type {HTMLDivElement}
     */
    const cover = document.getElementById('cover');
    /**
     * @type {HTMLAudioElement}
     */
    const audio = document.getElementById('audio');
    /**
     * @type {HTMLDivElement}
     */
    const loadingText = document.getElementById('loading-text');
    /**
     * @type {HTMLDivElement}
     */
    const startText = document.getElementById('start-text');
    /**
     * @type {HTMLDivElement}
     */
    const revealText = document.getElementById('reveal-text');
    /**
     * @type {HTMLDivElement}
     */
    const nextText = document.getElementById('next-text');
    /**
     * @type {HTMLDivElement}
     */
    const details = document.getElementById('details');

    /**
     * @type {CachedTrack}
     */
    let currentTrack = null;
    let state = 'start'; // one of: start, playing, reveal

    function start() {
        // Choose a random track, and display it blurred. Show start text
        state = 'start';
        console.info('start');

        audio.pause();
        details.textContent = '';

        if (cachedTracks.length == 0) {
            console.debug('cachedTracks still empty')
            setTimeout(start, 100);
            return;
        }

        currentTrack = cachedTracks.shift();

        cover.style.backgroundImage = `url("${currentTrack.imageBlobUrl}")`;
        audio.src = currentTrack.audioBlobUrl;
        cover.classList.add('blurred');
        startText.classList.remove('hidden');
        nextText.classList.add('hidden');
        loadingText.classList.add('hidden');
    }

    function play() {
        // Hide start text, start playing audio, show reveal text
        state = 'playing';
        console.info('playing');
        startText.classList.add('hidden');
        revealText.classList.remove('hidden');
        audio.play();
    }

    function reveal() {
        // Hide reveal text, show next text
        state = 'reveal'
        console.info('reveal');
        cover.classList.remove('blurred');
        revealText.classList.add('hidden');
        nextText.classList.remove('hidden');
        details.textContent = `${currentTrack.track.artists.join(',')} - ${currentTrack.track.title}`;
        if (currentTrack.track.album && currentTrack.track.album != currentTrack.track.title) {
            details.textContent += ` (${currentTrack.track.album}`;
            if (currentTrack.track.year) {
                details.textContent += `, ${currentTrack.track.year})`;
            } else {
                details.textContent += ')';
            }
        } else if (currentTrack.track.year) {
            details.textContent += ` (${currentTrack.track.year})`;
        }
    }

    async function init() {
        // Download track list
        const listResponse = await fetch('/track/list');
        const listJson = await listResponse.json();
        for (const playlist of listJson.playlists) {
            for (const track of playlist.tracks) {
                if (track.title && track.album && track.artists) {
                    tracks.push(track);
                }
            }
        }
        fillCachedTracks();
        setInterval(fillCachedTracks, 10000);
        start();
    }

    init();

    function onClick() {
        if (state == "start") {
            play();
        } else if (state == "playing") {
            reveal();
        } else if (state == "reveal") {
            start();
        }
    }

    document.addEventListener('click', onClick);
    document.addEventListener('keydown', event => {
        if (event.key == ' ') {
            onClick();
        }
    });
});
