// Ensures combined height of album cover and lyrics box never exceed 100vh

document.addEventListener('DOMContentLoaded', () => {
    const lyricsBox = document.getElementById('lyrics-box');
    const coverBox = document.getElementById('album-cover-box');
    let lastHeight = 0;

    function setMaxHeight(value) {
        coverBox.style.maxHeight = value;
        coverBox.style.maxWidth = value;
        lyricsBox.style.maxWidth = value;
    }

    function resizeCover() {
        if (lyricsBox.clientHeight == lastHeight) {
            return;
        }
        lastHeight = lyricsBox.clientHeight;

        // Do not set max height in single column interface
        if (window.innerWidth <= 900) {
            setMaxHeight('none');
            return;
        }

        if (lyricsBox.classList.contains('hidden')) {
            // No lyrics
            setMaxHeight(`calc(100vh - 2*var(--gap))`);
            return;
        }

        setMaxHeight(`calc(100vh - 3*var(--gap) - ${lyricsBox.clientHeight}px)`);

        console.debug('coversize: height changed:', lyricsBox.clientHeight);
    }

    const resizeObserver = new ResizeObserver(resizeCover);
    resizeObserver.observe(lyricsBox);
});
