/**
 * @param {string} url
 * @param {object} postDataObject
 * @returns {Promise<Response>}
 */
async function jsonPost(url, postDataObject, checkError = true) {
    postDataObject.csrf = getCsrfToken();
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

function getCsrfToken() {
    return document.getElementById('csrf-token').value;
}
