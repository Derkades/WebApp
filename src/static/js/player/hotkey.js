function handleKey(key) {
    // Don't perform hotkey actions when user is typing in a text field
    // But do still allow escape key
    if (document.activeElement.tagName === 'INPUT' &&
            key !== 'Escape') {
        console.debug('Ignoring keypress', key);
        return;
    }

    const keyInt = parseInt(key);
    if (!isNaN(keyInt)) {
        if (keyInt == 0) {
            return;
        }
        const checkboxes = document.getElementsByClassName('playlist-checkbox');
        if (checkboxes.length >= keyInt) {
            // Toggle checkbox
            checkboxes[keyInt-1].checked ^= 1;
        }
    } else if (key === 'p' || key === ' ') {
        const audioElem = getAudioElement();
        if (audioElem.paused) {
            audioElem.play().then(() => eventBus.publish(MusicEvent.PLAYBACK_CHANGE));
        } else {
            audioElem.pause();
            eventBus.publish(MusicEvent.PLAYBACK_CHANGE);
        }
    } else if (key === 'ArrowLeft') {
        queue.previous();
    } else if (key === 'ArrowRight') {
        queue.next();
    } else if (key === '.') {
        seek(3);
    } else if (key === ',') {
        seek(-3);
    } else if (key === 'Escape') {
        dialogs.closeTop();
    } else if (key === 'l') {
        switchLyrics();
    } else if (key === 'a') {
        switchAlbumCover();
    } else {
        console.debug('Unhandled keypress', key);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('keydown', event => handleKey(event.key));
});
