// Replace timestamp by formatted time string
document.addEventListener('DOMContentLoaded', () => {
    for (const elem of document.getElementsByClassName('format-timestamp')) {
        elem.textContent = timestampToString(elem.textContent);
    }

    for (const elem of document.getElementsByClassName('format-duration')) {
        elem.textContent = durationToString(elem.textContent);
    }
});

/**
 * @param {seconds} seconds
 * @returns {string} formatted duration
 */
function durationToString(seconds) {
    // If you modify this function, also copy it to util.js!
    const isoString = new Date(1000 * seconds).toISOString();
    const days = Math.floor(seconds / (24*60*60));
    const hours = parseInt(isoString.substring(11, 13)) + (days * 24);
    const mmss = isoString.substring(14, 19);
    if (hours == 0) {
        return mmss;
    } else {
        return hours + ':' + mmss;
    }
}

function timestampToString(seconds) {
    if (seconds == 0) {
        return '-';
    } else {
        return new Date(1000 * seconds).toLocaleString();
    }
}

function choice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function formatLargeNumber(number) {
    if (number > 1_000_000) {
        return (number / 1_000_000).toFixed(1) + 'M';
    } else if (number > 1_000) {
        return (number / 1_000).toFixed(1) + 'k';
    } else {
        return number + '';
    }
}

/**
 * Create button element containing an icon
 * @param {string} iconName
 * @returns {HTMLButtonElement}
 */
function createIconButton(iconName) {
    const button = document.createElement('button');
    button.classList.add('icon-button');
    const icon = document.createElement('div');
    icon.classList.add('icon');
    icon.style.backgroundImage = `url("/static/icon/${iconName}")`;
    button.appendChild(icon);
    return button;
}

/**
 * Replace icon in icon button
 * @param {HTMLButtonElement} iconButton
 * @param {string} iconName
 */
function replaceIconButton(iconButton, iconName) {
    const icon = iconButton.firstChild;
    icon.style.backgroundImage = `url("/static/icon/${iconName}")`
}
