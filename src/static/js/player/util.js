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

/**
 * @param {string} url
 * @param {object} postDataObject
 * @returns {Response}
 */
async function jsonPost(url, postDataObject, onErrorStatus) {
    postDataObject.csrf = await csrf.getToken();
    const options = {
        method: 'POST',
        body: JSON.stringify(postDataObject),
        headers: new Headers({
            'Content-Type': 'application/json'
        }),
    };
    const response = await fetch(new Request(url, options));
    if (onErrorStatus === undefined) {
        checkResponseCode(response);
    } else {
        onErrorStatus(response);
    }
    return response;
}
