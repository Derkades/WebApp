document.addEventListener('DOMContentLoaded', () => {
    const shareButton = document.getElementById('button-share');

    if (!shareButton) {
        // Not available in offline mode
        return;
    }

    shareButton.addEventListener('click', (async function() {
        if (!history.currentlyPlayingTrack) {
            // Music not loaded yet
            return;
        }

        const response = await jsonPost('/share/create', {track: history.currentlyPlayingTrack.path});
        const json = await response.json()
        window.open('/share/' + json.code, '_blank')
    }));
});
