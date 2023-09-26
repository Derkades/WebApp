// Replace timestamp by formatted time string
document.addEventListener('DOMContentLoaded', () => {
    for (const elem of document.getElementsByClassName('format-timestamp')) {
        elem.textContent = timestampToString(elem.textContent);
    }

    for (const elem of document.getElementsByClassName('format-duration')) {
        elem.textContent = secondsToString(elem.textContent);
    }
});

/**
 * @param {seconds} seconds
 * @returns {string} formatted duration
 */
function secondsToString(seconds) {
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
