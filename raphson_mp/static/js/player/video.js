document.addEventListener('DOMContentLoaded', () => {
    /** @type {HTMLButtonElement} */
    const videoButton = document.getElementById('button-video');
    if (videoButton == null) {
        console.warn('video: missing button, running in offline mode?');
        return;
    }

    /** @type {HTMLVideoElement} */
    const videoElem = document.getElementById('video');
    /** @type {HTMLAudioElement} */
    const audioElem = getAudioElement();

    videoButton.classList.add('hidden');

    function blur() {
        for (const elem of document.getElementsByClassName('cover-img')) {
            if (elem instanceof HTMLElement) {
                elem.style.filter = 'blur(10px)';
            }
        };
    }

    function resetBlur() {
        for (const elem of document.getElementsByClassName('cover-img')) {
            if (elem instanceof HTMLElement) {
                elem.style.filter = '';
            }
        };
    }

    videoButton.addEventListener('click', () => {
        const url =  queue.currentTrack.track.getVideoURL();
        console.info('video: set source', url);
        videoElem.src = url;
        videoButton.classList.add('hidden');
        blur();
        videoElem.play();

    });

    // Sync video time with audio
    audioElem.addEventListener('timeupdate', () => {
        if (!videoElem.hasAttribute('src')) {
            return;
        }

        if (audioElem.currentTime >= videoElem.duration) {
            return;
        }

        // Large difference => skip
        if (Math.abs(audioElem.currentTime - videoElem.currentTime) > 2) {
            console.info('video: skip from', videoElem.currentTime, 'to', audioElem.currentTime);
            videoElem.currentTime = audioElem.currentTime;
            return;
        }

        // Small difference => speed up or slow down video to catch up
        if (Math.abs(audioElem.currentTime - videoElem.currentTime) > 0.2) {
            if (videoElem.currentTime > audioElem.currentTime) {
                console.debug('video: slow down');
                videoElem.playbackRate = 0.9;
            } else {
                console.debug('video: speed up');
                videoElem.playbackRate = 1.1;
            }
            return;
        }

        console.debug('video: in sync');
    });

    audioElem.addEventListener('play', () => videoElem.play());
    audioElem.addEventListener('pause', () => videoElem.pause());

    eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => {
        videoElem.removeAttribute('src');
        videoElem.load();
        resetBlur();

        if (queue.currentTrack.track.video != null) {
            videoButton.classList.remove('hidden');
        }
    });
});
