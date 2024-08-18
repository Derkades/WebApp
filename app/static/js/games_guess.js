const music = new Music();

/** @type {Array<DownloadedTrack>} */
const downloadedTracks = [];

async function fillCachedTracks() {
    if (downloadedTracks.length > 3) {
        return;
    }

    /** @type {Playlist} */
    const playlist = choice(await music.playlists());

    const track = await playlist.chooseRandomTrack({}); // TODO only choose tracks with valid metadata (artist, album, title)
    const downloadedTrack = await track.download('webm_opus_high', false, false);
    downloadedTracks.push(downloadedTrack);
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
     * @type {DownloadedTrack}
     */
    let currentTrack = null;
    let state = 'start'; // one of: start, playing, reveal

    function start() {
        // Choose a random track, and display it blurred. Show start text
        state = 'start';
        console.info('start');

        audio.pause();
        details.textContent = '';

        if (downloadedTracks.length == 0) {
            console.debug('cachedTracks still empty')
            setTimeout(start, 100);
            return;
        }

        currentTrack = downloadedTracks.shift();

        cover.style.backgroundImage = `url("${currentTrack.imageUrl}")`;
        audio.src = currentTrack.audioUrl;
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

    (async function() {
        setInterval(fillCachedTracks, 2000);
        await fillCachedTracks();
        start();
    })();

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
