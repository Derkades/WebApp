document.addEventListener('DOMContentLoaded', () => {
    /** @type {HTMLButtonElement} */
    const videoButton = document.getElementById('button-video');
    if (videoButton == null) {
        console.warn('video: missing button, running in offline mode?');
        return;
    }

    /** @type {HTMLDivElement} */
    const videoBox = document.getElementById('video-box');
    /** @type {HTMLDivElement} */
    const albumCoverBox = document.getElementById('album-cover-box');
    /** @type {HTMLAudioElement} */
    const audioElem = getAudioElement();

    videoButton.hidden = true;

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

    function getVideoElement() {
        return document.getElementById('video');
    }

    // Replace album cover with video
    videoButton.addEventListener('click', () => {
        videoButton.hidden = true;
        const url =  queue.currentTrack.track.getVideoURL();
        console.info('video: set source', url);
        const videoElem = document.createElement('video');
        videoElem.setAttribute('muted', '');
        videoElem.src = url;
        videoElem.id = 'video';
        blur();
        videoBox.replaceChildren(videoElem);
        videoBox.hidden = false;
        document.getElementById('album-cover-box').hidden = true;
        if (!audioElem.paused) {
            videoElem.play();
        }
    });

    // Sync video time with audio
    audioElem.addEventListener('timeupdate', () => {
        const videoElem = getVideoElement();

        if (!videoElem) {
            return;
        }

        if (audioElem.currentTime >= videoElem.duration) {
            return;
        }

        // Large difference => skip
        if (Math.abs(audioElem.currentTime - videoElem.currentTime) > 1) {
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

    audioElem.addEventListener('play', () => {
        const videoElem = getVideoElement();
        if (videoElem) videoElem.play();
    });
    audioElem.addEventListener('pause', () => {
        const videoElem = getVideoElement();
        if (videoElem) videoElem.pause();
    });

    eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => {
        resetBlur();

        // cannot reliably remove source from video element, so we must remove the entire element
        // https://stackoverflow.com/q/79162209/4833737
        videoBox.replaceChildren();
        videoBox.hidden = true;

        // Make cover visible again
        albumCoverBox.hidden =false;

        videoButton.hidden = !queue.currentTrack.track.video;
    });
});
