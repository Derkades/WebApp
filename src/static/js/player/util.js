/**
 * Create button element containing an icon
 * @param {string} iconName
 * @param {Array<string>} classes
 * @returns {HTMLButtonElement}
 */
function createIconButton(iconName, classes) {
    const button = document.createElement('button');
    button.classList.add('icon-button');
    const icon = document.createElement('div');
    icon.classList.add('icon');
    icon.style.backgroundImage = `url("/static/icon/${iconName}")`;
    if (classes !== undefined) {
        icon.classList.add(...classes);
    }
    button.appendChild(icon);
    return button;
}

/**
 * Replace icon in icon button
 * @param {HTMLButtonElement} iconButton
 * @param {string} iconName
 */
function replaceIconButton(iconButton, iconName, classes) {
    const icon = iconButton.firstChild;
    icon.style.backgroundImage = `url("/static/icon/${iconName}")`
    if (classes !== undefined) {
        icon.classList.add(...classes);
    }
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

/**
 * @param {string} url
 * @param {object} postDataObject
 * @returns {Promise<Response>}
 */
async function jsonPost(url, postDataObject, checkError = true) {
    postDataObject.csrf = await csrf.getToken();
    const options = {
        method: 'POST',
        body: JSON.stringify(postDataObject),
        headers: new Headers({
            'Content-Type': 'application/json'
        }),
    };
    const response = await fetch(new Request(url, options));
    if (checkError) {
        checkResponseCode(response);
    }
    return response;
}

// https://stackoverflow.com/a/2117523
function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}
