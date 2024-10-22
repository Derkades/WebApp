document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();
    const lyricsElem = document.getElementById('lyrics-text');

    let lastLine = null;

    function updateLyrics() {
        const lyrics = queue.currentTrack.lyrics;
        const currentLine = lyrics.currentLine(audioElem.currentTime);

        if (currentLine == lastLine) {
            // Still the same line, no need to cause expensive DOM update.
            return;
        }

        lastLine = currentLine;

        // Show current line, with context
        const context = 3;
        let lyricsText = "";
        for (let i = currentLine - context; i <= currentLine + context; i++) {
            if (i < 0 || i >= lyrics.text.length) {
                lyricsText += '\n';
                continue;
            }
            lyricsText += lyrics.text[i].text + '\n';
        }

        lyricsElem.textContent = lyricsText;
    }

    function registerListener() {
        // When track changes, current state is no longer accurate
        lastLine = null;

        if (document.visibilityState == 'visible'
            && queue.currentTrack
            && queue.currentTrack.lyrics
            && queue.currentTrack.lyrics instanceof TimeSyncedLyrics) {
            console.debug('lyrics: registered timeupdate listener');
            audioElem.removeEventListener('timeupdate', updateLyrics); // remove it in case it is already registered
            audioElem.addEventListener('timeupdate', updateLyrics);
            return;
        } else {
            console.debug('lyrics: unregistered timeupdate listener');
            audioElem.removeEventListener('timeupdate', updateLyrics);
        }
    }

    eventBus.subscribe(MusicEvent.TRACK_CHANGE, registerListener);

    document.addEventListener('visibilitychange', registerListener);
});
