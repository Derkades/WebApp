function syncCookieWithInput(elemId) {
    const elem = document.getElementById(elemId);

    if (elem.dataset.restore === 'false') {
        return;
    }

    // If cookie exists, set input value to cookie value
    const value = getCookie(elemId);
    if (value !== null) {
        elem.value = value;
    }

    // If input value is updated, set cookie accordingly
    elem.addEventListener('input', event => {
        setCookie(elemId, event.target.value);
    });
}

function syncCookiesWithInputs() {
    [
        'settings-queue-size',
        'settings-audio-quality',
        'settings-volume',
        'settings-queue-removal-behaviour',
    ].forEach(syncCookieWithInput);
}

function youTubeDownload(event) {
    event.preventDefault();

    const output = document.getElementById('youtube-dl-output');
    output.style.backgroundColor = '';
    output.textContent = 'downloading...';

    const spinner = document.getElementById('youtube-dl-spinner');
    spinner.style.visibility = 'visible';

    const directory = document.getElementById('youtube-dl-directory').value;
    const url = document.getElementById('youtube-dl-url').value;

    const postBody = JSON.stringify({
        directory: directory,
        url: url,
    });

    const headers = new Headers({
        'Content-Type': 'application/json'
    });

    const options = {
        method: 'POST',
        body: postBody,
        headers: headers
    };

    fetch(new Request('/ytdl', options)).then(response => {
        if (response.status == 200) {
            spinner.style.visibility = 'hidden';
            response.json().then(json => {
                output.textContent = 'Status code: ' + json.code + '\n--- stdout ---\n' + json.stdout + '\n--- stderr ---\n' + json.stderr;
                output.style.backgroundColor = json.code === 0 ? 'darkgreen' : 'darkred';
            });
        } else {
            response.text().then(alert);
        }
    });
}
