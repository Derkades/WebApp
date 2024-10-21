document.addEventListener('DOMContentLoaded', () => {
    const audioElem = getAudioElement();
    const lyricsElem = document.getElementById('lyrics-text');

    // Handling time-synced lyrics
    audioElem.addEventListener('timeupdate', () => {
        if (!queue.currentTrack){
            console.warn('lyrics: no current track');
        }

        const lyrics = queue.currentTrack.lyrics;
        if (lyrics instanceof TimeSyncedLyrics) {
            const currentLine = lyrics.currentLine(audioElem.currentTime);

            // Show current line, with context
            const context = 3;
            let lyricsText = "";
            for (let i = currentLine - context; i <= currentLine + context; i++) {
                if (i < 0 || i >= lyrics.text.length) {
                    continue;
                }
                lyricsText += lyrics.text[i].text + '\n';
            }

            lyricsElem.textContent = lyricsText;
        }
    });
});
