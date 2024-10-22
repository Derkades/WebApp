document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();
    const lyricsElem = document.getElementById('lyrics-box');

    let lastLine = null;

    function updateSyncedLyrics() {
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
            audioElem.removeEventListener('timeupdate', updateSyncedLyrics); // remove it in case it is already registered
            audioElem.addEventListener('timeupdate', updateSyncedLyrics);
            return;
        } else {
            console.debug('lyrics: unregistered timeupdate listener');
            audioElem.removeEventListener('timeupdate', updateSyncedLyrics);
        }
    }

    function replaceLyrics() {
        const queuedTrack = queue.currentTrack;
        const lyricsElem = document.getElementById('lyrics-box')

        if (queuedTrack.lyrics) {
            lyricsElem.classList.remove('hidden');
            if (queuedTrack.lyrics instanceof PlainLyrics) {
                lyricsElem.textContent = queuedTrack.lyrics.text;
            }
            // time-synced lyrics is handled by updateSyncedLyrics
        } else {
            lyricsElem.classList.add('hidden');
        }
    }

    eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => {
        registerListener();
        replaceLyrics();
    });

    document.addEventListener('visibilitychange', registerListener);
});
