function syncCookieWithInput(elemId) {
    const elem = document.getElementById(elemId);
    const isCheckbox = elem.matches('input[type="checkbox"]');

    if (elem.dataset.restore === 'false') {
        return;
    }

    // If cookie exists, set input value to cookie value
    const value = getCookie(elemId);
    if (value !== null) {
        if (isCheckbox) {
            elem.checked = value === '1';
        } else {
            elem.value = value;
        }
    }

    // If input value is updated, set cookie accordingly
    elem.addEventListener('input', event => {
        if (isCheckbox) {
            setCookie(elemId, event.target.checked ? '1' : '0');
        } else {
            setCookie(elemId, event.target.value);
        }
    });
}

function syncCookiesWithInputs() {
    [
        'settings-queue-size',
        'settings-audio-type',
        'settings-volume',
        'settings-queue-removal-behaviour',
        'settings-download-mode',
        // 'settings-theme',
        'settings-meme-mode',
        'settings-language',
    ].forEach(syncCookieWithInput);

    onVolumeChange();
}

function youTubeDownload(event) {
    event.preventDefault();

    const output = document.getElementById('youtube-dl-output');
    output.style.backgroundColor = '';
    output.textContent = 'Starting download...\n';

    const spinner = document.getElementById('youtube-dl-spinner');
    spinner.classList.remove('hidden');

    const directory = document.getElementById('youtube-dl-directory').value;
    const url = document.getElementById('youtube-dl-url').value;

    (async function(){
        const decoder = new TextDecoder();

        function handleResponse(result) {
            output.textContent += decoder.decode(result.value);
            output.scrollTop = output.scrollHeight;
            return result
        }

        const response = await jsonPost('/ytdl', {directory: directory, url: url});
        const reader = await response.body.getReader();
        await reader.read().then(function process(result) {
            if (result.done) {
                console.log("stream done");
                return reader.closed;
            }
            return reader.read().then(handleResponse).then(process)
        });

        await Track.updateLocalTrackList();

        if (output.textContent.endsWith('Done!')) {
            output.style.backgroundColor = 'darkgreen';
        } else {
            output.style.backgroundColor = 'darkred';
        }
    })().then(() => {
        spinner.classList.add('hidden');
    }).catch(err => {
        console.error(err);
        spinner.classList.add('hidden');
        alert('error, check console');
    });
}
