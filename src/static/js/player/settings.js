function syncInputWithStorage(elemId) {
    const elem = document.getElementById(elemId);
    const isCheckbox = elem.matches('input[type="checkbox"]');

    if (elem.dataset.restore === 'false') {
        return;
    }

    // Initialize input form local storage
    const value = window.localStorage.getItem(elemId);
    if (value !== null) {
        if (isCheckbox) {
            elem.checked = value === 'true';
        } else {
            elem.value = value;
        }
    }

    // If input value is updated, change storage accordingly
    elem.addEventListener('input', event => {
        const value = isCheckbox ? event.target.checked : event.target.value;
        window.localStorage.setItem(elemId, value);
    });
}

function syncInputsWithStorage() {
    [
        'settings-queue-size',
        'settings-audio-type',
        'settings-volume',
        'settings-queue-removal-behaviour',
        'settings-download-mode',
        // 'settings-theme',
        'settings-meme-mode',
        // 'settings-language',
    ].forEach(syncInputWithStorage);

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

document.addEventListener('DOMContentLoaded', () => {
    syncInputsWithStorage();

    document.getElementById('youtube-dl-submit').addEventListener('click', youTubeDownload);

    document.getElementById('scan-button').addEventListener('click', () => (async function() {
        const spinner = document.getElementById('scan-spinner');
        const button = document.getElementById('scan-button');
        spinner.classList.remove('hidden');
        button.classList.add('hidden');
        await jsonPost('/scan_music', {});
        await Track.updateLocalTrackList();
        spinner.classList.add('hidden');
        button.classList.remove('hidden');
    })());

    document.getElementById('settings-queue-size').addEventListener('input', () => queue.fill());
});
