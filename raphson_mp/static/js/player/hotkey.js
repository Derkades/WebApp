const VOLUME_HOTKEY_CHANGE = 5;

function handleKey(event) {
    const key = event.key;

    // Don't perform hotkey actions when user is typing in a text field
    // But do still allow escape key
    if (document.activeElement.tagName === 'INPUT' &&
            key !== 'Escape') {
        console.debug('hotkey: ignoring keypress:', key);
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
        savePlaylistState();
    } else if (key === 'p' || key === ' ') {
        const audioElem = getAudioElement();
        if (audioElem.paused) {
            audioElem.play();
        } else {
            audioElem.pause();
        }
    } else if (key === 'ArrowLeft') {
        queue.previous();
    } else if (key === 'ArrowRight') {
        queue.next();
    } else if (key == 'ArrowUp') {
        const slider = document.getElementById('settings-volume');
        if (parseInt(slider.value) < 100 - VOLUME_HOTKEY_CHANGE) {
            slider.value = parseInt(slider.value) + VOLUME_HOTKEY_CHANGE;
        } else {
            slider.value = 100;
        }
        onVolumeChange();
    } else if (key == 'ArrowDown') {
        const slider = document.getElementById('settings-volume');
        if (parseInt(slider.value) > VOLUME_HOTKEY_CHANGE) {
            slider.value = parseInt(slider.value) - VOLUME_HOTKEY_CHANGE;
        } else {
            slider.value = 0;
        }
        onVolumeChange();
    } else if (key === '.' || key == '>') {
        seekRelative(3);
    } else if (key === ',' || key == '<') {
        seekRelative(-3);
    } else if (key === 'Escape') {
        dialogs.closeTop();
    } else if (key == '/') {
        event.preventDefault(true);
        document.getElementById('open-dialog-search').click();
    } else {
        console.debug('hotkey: unhandled keypress:', key);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('keydown', handleKey);
});
