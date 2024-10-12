document.addEventListener('DOMContentLoaded', () => {
    const trackChooseCount = 5;
    const firstPlayRange = [5000, 30000];
    const playRange = [1000, 25000];
    const pauseRange = [1500, 8000];

    /** @type {HTMLDivElement} */
    const boxes = document.getElementById('boxes');
    /** @type {HTMLAudioElement} */
    const audio = document.getElementById('audio');

    const textChoose = document.getElementById('text-choose');
    const textStart = document.getElementById('text-start');
    const spinner = document.getElementById('spinner');

    let downloadedTrack = null;

    /**
     * @param {Track} track
     */
    async function choose(track) {
        textChoose.classList.add('hidden');
        boxes.replaceChildren();

        spinner.classList.remove('hidden');

        downloadedTrack = await track.download();

        const box = document.createElement('div')
        box.classList.add('box', 'cover-img');
        box.id = 'cover';
        box.style.backgroundImage = `url("${downloadedTrack.imageUrl}")`;
        boxes.replaceChildren(box);

        window.addEventListener('click', start);
        window.addEventListener('keydown', start);

        audio.src = downloadedTrack.audioUrl;

        spinner.classList.add('hidden');
        textStart.classList.remove('hidden');
    }

    function start() {
        console.debug('start');
        window.removeEventListener('click', start);
        window.removeEventListener('keydown', start);
        textStart.classList.add('hidden');
        audio.play();
        setTimeout(pause, randInt(...firstPlayRange));
    }

    function play() {
        console.debug('play');
        audio.play();
        document.getElementById('cover').style.scale = null;
        setTimeout(pause, randInt(...playRange));
    }

    function pause() {
        console.debug('pause');
        audio.pause();
        document.getElementById('cover').style.scale = 0;
        setTimeout(play, randInt(...pauseRange));
    }

    async function init() {
        const playlists = await music.playlists();

        for (let tracks = 0; tracks < trackChooseCount;) {
            /** @type {Playlist} */
            const playlist = choice(playlists);
            const track = await playlist.chooseRandomTrack();
            const box = document.createElement('div');
            box.classList.add('box', 'choose');
            box.textContent = track.displayText(true);
            box.addEventListener('click', () => {
                choose(track);
            });
            boxes.append(box);
            tracks++;
        }
    }

    audio.addEventListener('ended', () => window.location = '');

    init();
});
