// Unmaintained, not up to date with many changes throughout the codebase

function round(number) {
    return Math.round((number + Number.EPSILON) * 100) / 100;
}

let totalDownloadedSizeMiB = 0;

function updateTotal(newTotal) {
    totalDownloadedSizeMiB = newTotal;
    document.getElementById('total-size-mib').textContent = round(totalDownloadedSizeMiB);
}

function addToTotal(add) {
    updateTotal(totalDownloadedSizeMiB + add);
}

/**
 * @param {string} selectedPlaylist
 * @param {IDBDatabase} db
 */
async function updateTrackList(selectedPlaylist, db) {
    const response = await fetch('/track/list');
    const json = await response.json();

    document.getElementById('table-body').replaceChildren();
    document.getElementById('table-body-downloaded').replaceChildren();
    updateTotal(0);

    const tx = db.transaction('audio', 'readonly');

    for (const playlist of json.playlists) {
        if (playlist.name !== selectedPlaylist) {
            continue;
        }

        for (const track of playlist.tracks) {
            const req = tx.objectStore('audio').get(track.path);
            req.onerror = () => console.warn(req);

            req.onsuccess = () => {
                /** @type {ArrayBuffer | undefined} */
                const buffer = req.result;
                if (buffer === undefined) {
                    const downloadedCol = document.createElement('td');
                    downloadedCol.classList.add('icon-col');

                    const titleCol = document.createElement('td');
                    titleCol.textContent = track.path;

                    const row = document.createElement('tr');
                    row.dataset.path = track.path;
                    row.append(downloadedCol, titleCol);
                    document.getElementById('table-body').appendChild(row);
                } else {
                    const sizeCol = document.createElement('td');
                    const sizeMiB = buffer.byteLength / (1024*1024);
                    addToTotal(sizeMiB);
                    sizeCol.textContent = round(sizeMiB) + " MiB";
                    const titleCol = document.createElement('td');
                    titleCol.textContent = track.path;
                    const row = document.createElement('tr');
                    row.append(sizeCol, titleCol);
                    document.getElementById('table-body-downloaded').appendChild(row);
                }
            }
        }
    }
};

/**
 * @param {IDBDatabase} db
 */
async function downloadTracks(db) {
    const tableBody = document.getElementById('table-body');
    for (const row of tableBody.childNodes) {
        const downloadCol = row.childNodes[0];
        downloadCol.textContent = '...';
        const path = row.dataset.path;
        const audioUrl = '/track/audio?type=webm_opus_high&path=' + encodeURIComponent(path);
        const response = await fetch(audioUrl);
        if (response.status != 200) {
            throw new Error("Error status " + response.status);
        }
        const audioData = await response.arrayBuffer();
        const tx = db.transaction('audio', 'readwrite');
        tx.objectStore('audio').add(audioData, path);
        tx.oncomplete = () => {
            downloadCol.textContent = 'yes';
        };
    };
};

function openDatabase(callback) {
    const dbRequest = window.indexedDB.open('tracks', 1);

    dbRequest.onerror = () => alert('cannot open indexedDB');

    dbRequest.onupgradeneeded = () => {
        const db = dbRequest.result;
        const store = db.createObjectStore('audio');
    };

    dbRequest.onsuccess = async function() {
        const db = dbRequest.result;
        callback(db);
    };
}

// Replace timestamp by formatted time string
document.addEventListener('DOMContentLoaded', () => {
    openDatabase(db => {
        const select = document.getElementById('select-playlist');

        if (select.value != "dummy") {
            document.getElementById('dummy-value').remove();
            const playlist = select.value;
            updateTrackList(playlist, db);
        }

        document.getElementById('select-playlist').oninput = event => {
            const dummy = document.getElementById('dummy-value');
            if (dummy !== null) {
                dummy.remove();
            }
            const playlist = event.target.value;
            updateTrackList(playlist, db);
        };

        const downloadButton = document.getElementById('download-button');
        downloadButton.onclick = () => downloadTracks(db);
    });
});
