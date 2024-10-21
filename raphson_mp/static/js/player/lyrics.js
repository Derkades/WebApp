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
            lyricsElem.style.fontSize = '1.2em';
            const currentLine = lyrics.currentLine(audioElem.currentTime);
            console.log(currentLine);
            lyricsElem.textContent = "";

            // Show current line, with context
            const context = 3;
            for (let i = currentLine - context; i <= currentLine + context; i++) {
                if (i < 0 || i >= lyrics.text.length) {
                    continue;
                }
                lyricsElem.textContent += lyrics.text[i].text + '\n';
            }
        }
    });
});
