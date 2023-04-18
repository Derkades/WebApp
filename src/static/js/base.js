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

// https://www.w3schools.com/js/js_cookies.asp
function setCookie(cname, cvalue) {
    const d = new Date();
    d.setTime(d.getTime() + (365*24*60*60*1000));
    const expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/;SameSite=Strict";
}

/**
 * @param {string} cname cookie name
 * @returns {string} cookie value
 */
function getCookie(cname) {
    const name = cname + "=";
    const decodedCookie = decodeURIComponent(document.cookie);
    const ca = decodedCookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return null;
}

function choice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Throw error if response status code is an error code
 * @param {Response} response
 */
function checkResponseCode(response) {
    if (response.status != 200) {
        throw 'response code ' + response.status;
    }
}
