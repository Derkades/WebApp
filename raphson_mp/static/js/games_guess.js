/** @type {Array<DownloadedTrack>} */
const downloadedTracks = [];

document.addEventListener('DOMContentLoaded', () => {
    /** @type {HTMLDivElement} */
    const playlists = document.getElementById('playlists');
    /** @type {HTMLDivElement} */
    const cover = document.getElementById('cover');
    /** @type {HTMLAudioElement} */
    const audio = document.getElementById('audio');
    /** @type {HTMLDivElement} */
    const loadingText = document.getElementById('loading-text');
    /** @type {HTMLDivElement} */
    const startText = document.getElementById('start-text');
    /** @type {HTMLDivElement} */
    const revealText = document.getElementById('reveal-text');
    /** @type {HTMLDivElement} */
    const nextText = document.getElementById('next-text');
    /** @type {HTMLDivElement} */
    const details = document.getElementById('details');

    /** @type {DownloadedTrack} */
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
        details.textContent = currentTrack.track.displayText(true, true);
    }

    function onClick() {
        if (state == "start") {
            play();
        } else if (state == "playing") {
            reveal();
        } else if (state == "reveal") {
            start();
        }
    }

    cover.addEventListener('click', onClick);
    document.addEventListener('keydown', event => {
        if (event.key == ' ') {
            onClick();
        }
    });

    async function fillCachedTracks() {
        if (downloadedTracks.length > 2) {
            return;
        }

        const enabledPlaylists = [];

        for (const input of playlists.getElementsByTagName('input')) {
            if (input.checked) {
                enabledPlaylists.push(input.dataset.playlist);
            }
        }

        if (enabledPlaylists.length == 0) {
            return;
        }

        const playlistName = choice(enabledPlaylists);
        const playlist = await music.playlist(playlistName);
        const track = await playlist.chooseRandomTrack(true, {});
        const downloadedTrack = await track.download();
        downloadedTracks.push(downloadedTrack);
    }

    setInterval(fillCachedTracks, 2000);
    fillCachedTracks(); // intentionally not awaited
    start();

    (async () => {
        const checkboxes = await music.getPlaylistCheckboxes();
        for (const input of checkboxes.getElementsByTagName('input')) {
            input.addEventListener('input', () => {
                downloadedTracks.length = 0;
                fillCachedTracks();
            });
        }
        playlists.replaceChildren(checkboxes);
    })();
});
