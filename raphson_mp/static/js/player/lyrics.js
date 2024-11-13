document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();
    const lyricsElem = document.getElementById('lyrics-box');
    const lyricsSetting = document.getElementById('settings-lyrics');

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
        const lyricsHtml = [];
        for (let i = currentLine - context; i <= currentLine + context; i++) {
            if (i >= 0 && i < lyrics.text.length) {
                const lineHtml = document.createElement('span');
                lineHtml.textContent = lyrics.text[i].text;
                if (i != currentLine) {
                    lineHtml.classList.add('secondary-large');
                }
                lyricsHtml.push(lineHtml);
            }
            lyricsHtml.push(document.createElement('br'));
        }

        lyricsElem.replaceChildren(...lyricsHtml);
    }

    function registerListener() {
        // When track changes, current state is no longer accurate
        lastLine = null;

        if (document.visibilityState == 'visible'
            && queue.currentTrack
            && queue.currentTrack.lyrics
            && queue.currentTrack.lyrics instanceof TimeSyncedLyrics
            && lyricsSetting.checked
        ) {
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
        const lyricsElem = document.getElementById('lyrics-box');

        const hasLyrics = queuedTrack && queuedTrack.lyrics && lyricsSetting.checked;

        lyricsElem.hidden = !hasLyrics;

        if (hasLyrics && queuedTrack.lyrics instanceof PlainLyrics) {
            lyricsElem.textContent = queuedTrack.lyrics.text;
        }

        // time-synced lyrics is handled by updateSyncedLyrics
        registerListener();
    }

    eventBus.subscribe(MusicEvent.TRACK_CHANGE, replaceLyrics);
    eventBus.subscribe(MusicEvent.SETTINGS_LOADED, replaceLyrics);

    // Listener is only registered if page is visible, so if page visibility
    // changes we must register (or unregister) the listener.
    document.addEventListener('visibilitychange', registerListener)

    // Quick toggle for lyrics setting
    document.getElementById('album-cover-box').addEventListener('click', () => {
        lyricsSetting.checked = !lyricsSetting.checked;
        replaceLyrics();
    });

    // Handle lyrics setting being changed
    lyricsSetting.addEventListener('change', replaceLyrics);
});
