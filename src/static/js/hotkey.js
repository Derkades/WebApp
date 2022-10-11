function handleKey(key) {
    // Don't perform hotkey actions when user is typing in a text field
    if (document.activeElement.tagName === 'INPUT') {
        console.log('Ignoring keypress', key);
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
            // Save to cookies
            saveCheckboxState();
        }
    } else if (key === 'p' || key === ' ') {
        playPause();
    } else if (key === 'ArrowLeft') {
        queue.previous();
    } else if (key === 'ArrowRight') {
        queue.next();
    } else if (key === '.') {
        seek(3);
    } else if (key === ',') {
        seek(-3);
    } else {
        console.log('Unhandled keypress', key);
    }
}
