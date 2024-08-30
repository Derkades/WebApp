"use strict";

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

function randInt(min, max) {
    return Math.floor(Math.random() * (max - min)) + min;
}

function choice(arr) {
    return arr[randInt(0, arr.length)];
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
    icon.classList.add('icon', 'icon-' + iconName);
    button.appendChild(icon);
    return button;
}

/**
 * Replace icon in icon button
 * @param {HTMLButtonElement} iconButton
 * @param {string} iconName
 */
function replaceIconButton(iconButton, iconName) {
    /** @type {HTMLElement} */
    const icon = iconButton.firstChild;
    icon.classList.remove(...icon.classList.values());
    icon.classList.add('icon', 'icon-' + iconName);
}

/**
 * Throw error if response status code is an error code
 * @param {Response} response
 */
function checkResponseCode(response) {
    if (!response.ok) {
        throw 'response code ' + response.status;
    }
}

// https://stackoverflow.com/a/2117523
function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

function getCsrfToken() {
    return document.getElementById('csrf-token').textContent;
}

function dedup(array) {
    const array2 = [];
    const set = new Set();
    for (const elem of array) {
        if (!set.has(elem)) {
            set.add(elem);
            array2.push(elem);
        }
    }
    return array2;
}
