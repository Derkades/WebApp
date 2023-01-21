function createIconButton(iconName, classes) {
    const button = document.createElement('button');
    button.classList.add('icon-button');
    const icon = document.createElement('div');
    icon.classList.add('icon');
    icon.style.backgroundImage = "url('/static/icon/" + iconName + "')";
    if (classes !== undefined) {
        icon.classList.add(...classes);
    }
    button.appendChild(icon);
    return button;
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

/**
 * @param {seconds} seconds
 * @returns {string} formatted duration
 */
function secondsToString(seconds) {
    const hhmmss =  new Date(1000 * seconds).toISOString().substring(11, 19);
    if (hhmmss.startsWith('00:')) {
        return hhmmss.substring(3);
    } else {
        return hhmmss;
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

// https://www.tutorialspoint.com/levenshtein-distance-in-javascript
function levenshtein(str1, str2) {
    const track = Array(str2.length + 1).fill(null).map(() =>
    Array(str1.length + 1).fill(null));
    for (let i = 0; i <= str1.length; i += 1) {
        track[0][i] = i;
    }
    for (let j = 0; j <= str2.length; j += 1) {
        track[j][0] = j;
    }
    for (let j = 1; j <= str2.length; j += 1) {
        for (let i = 1; i <= str1.length; i += 1) {
            const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
            track[j][i] = Math.min(
                track[j][i - 1] + 1,
                track[j - 1][i] + 1,
                track[j - 1][i - 1] + indicator,
            );
        }
    }
    return track[str2.length][str1.length];
};

/**
 * @returns {string} CSRF token
 */
function getCsrfToken() {
    return document.getElementById('csrf-token').textContent;
}

async function refreshCsrfToken() {
    const response = await fetch('/get_csrf');
    checkResponseCode(response);
    const json = await response.json();
    const token = json.token;
    document.getElementById('csrf-token').textContent = token;
}

/**
 * @param {string} url
 * @param {object} postDataObject
 * @returns {Response}
 */
async function jsonPost(url, postDataObject) {
    postDataObject.csrf = getCsrfToken();
    const options = {
        method: 'POST',
        body: JSON.stringify(postDataObject),
        headers: new Headers({
            'Content-Type': 'application/json'
        }),
    };
    const response = await fetch(new Request(url, options));
    checkResponseCode(response);
    return response;
}
