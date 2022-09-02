"use strict";

document.queue = [];
document.queueBusy = false;
document.queueSize = 5;
document.quality = 'high';

// https://www.w3schools.com/js/js_cookies.asp
function setCookie(cname, cvalue) {
    const d = new Date();
    d.setTime(d.getTime() + (365*24*60*60*1000));
    const expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/;SameSite=Strict";
}

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

document.addEventListener("DOMContentLoaded", () => {
    const cookieQueueSize = getCookie('settings-queue-size');
    if (cookieQueueSize !== null) {
        document.queueSize = parseInt(cookieQueueSize);
        document.getElementById('queue-size').value = cookieQueueSize;
    }

    const cookieAudioQuality = getCookie('settings-audio-quality')
    if (cookieAudioQuality !== null) {
        document.quality = cookieAudioQuality;
        document.getElementById('audio-quality').value = cookieAudioQuality
    }

    // Playback controls
    document.getElementById('button-backward-fast').addEventListener('click', () => seek(-30));
    document.getElementById('button-backward').addEventListener('click', () => seek(-5));
    document.getElementById('button-play').addEventListener('click', play);
    document.getElementById('button-pause').addEventListener('click', pause);
    document.getElementById('button-forward').addEventListener('click', () => seek(5));
    document.getElementById('button-forward-fast').addEventListener('click', () => seek(30));
    document.getElementById('button-forward-step').addEventListener('click', liedje);

    // Lyrics
    document.getElementById('button-closed-captioning').addEventListener('click', switchLyrics);
    document.getElementById('button-record-vinyl').addEventListener('click', switchAlbumCover);
    document.getElementById('button-record-vinyl').style.display = 'none';

    // Settings overlay
    document.getElementById('button-gear').addEventListener('click', () =>
            document.getElementById('settings-overlay').style.display = 'flex');
    document.getElementById('settings-close').addEventListener('click', () =>
            document.getElementById('settings-overlay').style.display = 'none');
    document.getElementById('youtube-dl-submit').addEventListener('click', youTubeDownload);
    document.getElementById('queue-size').addEventListener('input', event => {
        document.queueSize = parseInt(event.data);
        setCookie('settings-queue-size', event.data);
        updateQueue();
    });
    document.getElementById('audio-quality').addEventListener('input', event => {
        document.quality = event.target.value;
        setCookie('settings-audio-quality', document.quality);
    });

    // Queue overlay
    document.getElementById('button-square-plus').addEventListener('click', () =>
            document.getElementById('queue-overlay').style.display = 'flex');
    document.getElementById('queue-close').addEventListener('click', () =>
            document.getElementById('queue-overlay').style.display = 'none');
    document.getElementById('track-list-person').addEventListener('input', searchTrackList);
    document.getElementById('track-list-query').addEventListener('input', searchTrackList);

    // Hotkeys
    document.addEventListener('keydown', event => handleKey(event.key));

    updateQueue();
    liedje();
    setInterval(showCorrectPlayPauseButton, 50);
    initTrackList();
    searchTrackList();
});

function handleKey(key) {
    // Don't perform hotkey actions when user is typing in a text field
    if (document.activeElement.tagName === 'INPUT') {
        console.log('Ignoring keypress', key)
        return;
    }

    const keyInt = parseInt(key);
    if (!isNaN(keyInt)) {
        let index = 1;
        for (const checkbox of document.getElementsByClassName('person-checkbox')) {
            if (index === keyInt) {
                checkbox.checked = !checkbox.checked
                break;
            }
            index++;
        }
    } else if (key === 'p' || key === ' ') {
        const audioElem = getAudioElement();
        if (audioElem == null) {
            return;
        }
        if (audioElem.paused) {
            audioElem.play();
        } else {
            audioElem.pause();
        }
    } else if (key === 'ArrowRight' || key === 'f') {
        liedje();
    } else if (key === '.') {
        seek(3);
    } else if (key === ',') {
        seek(-3);
    } else {
        console.log('Unhandled keypress', key)
    }
}

function getAudioElement() {
    const audioDiv = document.getElementById('audio');
    if (audioDiv.children.length === 1) {
        return audioDiv.children[0];
    }
    return null;
}

function replaceAudioElement(newElement) {
    const audioDiv = document.getElementById('audio');
    audioDiv.innerHTML = '';
    audioDiv.appendChild(newElement);
}

function play() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    audioElem.play();
}

function pause() {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    audioElem.pause();
}

function showCorrectPlayPauseButton() {
    const audioElem = getAudioElement();
    if (audioElem == null || audioElem.paused) {
        document.getElementById('button-pause').style.display = 'none';
        document.getElementById('button-play').style.display = '';
    } else {
        document.getElementById('button-play').style.display = 'none';
        document.getElementById('button-pause').style.display = '';
    }

}

function seek(delta) {
    const audioElem = getAudioElement();
    if (audioElem == null) {
        return;
    }
    const newTime = audioElem.currentTime + delta;
    if (delta > 0 && newTime < audioElem.duration ||
        delta < 0 && newTime > 0) {
        audioElem.currentTime = newTime;
    }
}

function liedje() {
    if (document.queue.length === 0) {
        console.log('queue is empty, trying again later');
        setTimeout(liedje, 1000);
        return;
    }

    // Get and remove first item from queue
    const track = getTrackFromQueue();

    const audioElem = createAudioElement(track.audioBlobUrl);
    replaceAudioElement(audioElem);

    replaceAlbumImages(track.imageBlobUrl);

    if (track.lyrics.found) {
        // track.lyrics.html is already escaped by backend, and only contains some safe HTML that we should not escape
        const source = '<a class="secondary" href="' + escapeHtml(track.lyrics.genius_url) + '" target="_blank">Source</a>'
        document.getElementById('lyrics').innerHTML = track.lyrics.html + '<br><br>' + source;
    } else {
        document.getElementById('lyrics').innerHTML = '<i class="secondary">Geen lyrics gevonden</i>'
    }

    // Replace 'currently playing' text
    const currentTrackElem = document.getElementById('current-track');
    const previousTrackElem = document.getElementById('previous-track');
    previousTrackElem.innerText = currentTrackElem.innerText;
    currentTrackElem.innerText = '[' + track.personDisplay + '] ' + track.displayName;

    updateQueue();
}

function replaceAlbumImages(imageUrl) {
    const cssUrl = 'url("' + imageUrl + '")';

    const bg1 = document.getElementById('bg-image-1');
    const bg2 = document.getElementById('bg-image-2');
    const fg1 = document.getElementById('album-cover-1');
    const fg2 = document.getElementById('album-cover-2');

    // Set bottom (1) to new image
    bg1.style.backgroundImage = cssUrl;
    fg1.style.backgroundImage = cssUrl;

    // Slowly fade out old image (2)
    bg2.style.opacity = 0;
    fg2.style.opacity = 0;

    setTimeout(() => {
        // To prepare for next replacement, move bottom image (1) to top image (2)
        bg2.style.backgroundImage = cssUrl;
        fg2.style.backgroundImage = cssUrl;
        // Make it visible
        bg2.style.opacity = 1;
        fg2.style.opacity = 1;
    }, 1000);
}

function getActivePersons() {
    const active = [];

    for (const checkbox of document.getElementsByClassName('person-checkbox')) {
        const musicDirName = checkbox.id.substring(9); // remove 'checkbox-'
        if (checkbox.checked) {
            active.push(musicDirName);
        }
    }

    return active;
}

function updateProgress(audioElem) {
    const current = secondsToString(Math.floor(audioElem.currentTime));
    const max = secondsToString(Math.floor(audioElem.duration));
    const percentage = (audioElem.currentTime / audioElem.duration) * 100;

    document.getElementById('progress-time-current').innerText = current;
    document.getElementById('progress-time-duration').innerText = max;
    document.getElementById('progress-bar').style.width = percentage + '%';
}

function createAudioElement(sourceUrl) {
    const audioElem = document.createElement('audio');
    const sourceElem = document.createElement('source');
    sourceElem.src = sourceUrl;
    audioElem.appendChild(sourceElem);
    audioElem.setAttribute('autoplay', '');
    audioElem.onended = liedje;
    audioElem.ontimeupdate = () => updateProgress(audioElem);
    return audioElem;
}

function choice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function getNextPerson(currentPerson) {
    const active = getActivePersons();

    let person;

    if (active.length === 0) {
        // No one is selected
        // eigenlijk zou er een error moeten komen, maar voor nu kiezen we DK
        person = "DK";
    } else if (currentPerson === undefined) {
        // No person chosen yet, choose random person
        person = choice(active);
    } else {
        const currentIndex = active.indexOf(currentPerson);
        if (currentIndex === -1) {
            // Current person is no longer active, we don't know the logical next person
            // Choose random person
            person = choice(active);
        } else {
            // Choose next person in list, wrapping around if at the end
            person = active[(currentIndex + 1) % active.length];
        }
    }

    return person;
}

function throwErr(err) {
    throw err;
}

function updateQueue() {
    if (document.queueBusy) {
        return;
    }

    updateQueueHtml();

    let person;

    if (document.queue.length > 0) {
        const lastTrack = document.queue[document.queue.length - 1];
        const lastPerson = lastTrack.person;
        person = getNextPerson(lastPerson);
    } else {
        person = getNextPerson();
    }

    if (document.queue.length >= document.queueSize) {
        return;
    }

    document.queueBusy = true;

    const trackData = {
        person: person,
        personDisplay: person.startsWith("Guest-") ? person.substring('6') : person,
    }

    console.info('queue | choose track');

    fetch(new Request('/choose_track?person_dir=' + encodeURIComponent(person)))
        .then(response => {
            if (response.status == 200) {
                return response.json();
            } else {
                throw 'response code ' + response.status;
            }
        }, throwErr)
        .then(trackJson => {
            trackData.name = trackJson.name;
            trackData.displayName = trackJson.display_name;
            downloadAndAddToQueue(trackData, () => {
                // On complete
                document.queueBusy = false;
                setTimeout(updateQueue, 500);
            });
        }, error => {
            console.warn('queue | error');
            console.warn(error);
            document.queueBusy = false
            setTimeout(updateQueue, 5000);
        });
}

function downloadAndAddToQueue(trackData, onComplete) {
    // JavaScript doesn't stop execution of a promise chain in case of an error, so we need to manually
    // pass the error down the chain by repeatedly calling throwErr() on errors.
    trackData.queryString = '?person_dir=' + encodeURIComponent(trackData.person) + '&track_name=' + encodeURIComponent(trackData.name);
    trackData.audioStreamUrl = '/get_track' + trackData.queryString + '&quality=' + encodeURIComponent(document.quality);
    console.info('queue | download audio');
    fetch(new Request(trackData.audioStreamUrl))
        .then(response => {
            if (response.status == 200) {
                return response.blob();
            } else {
                throw 'response code ' + response.status;
            }
        }, throwErr)
        .then(audioBlob => {
            trackData.audioBlobUrl = URL.createObjectURL(audioBlob);
            console.info('queue | download album cover image');
            trackData.imageStreamUrl = '/get_album_cover' + trackData.queryString;
            return fetch(new Request(trackData.imageStreamUrl));
        }, throwErr)
        .then(response => {
            if (response.status == 200) {
                return response.blob();
            } else {
                throw 'response code ' + response.status;
            }
        }, throwErr)
        .then(imageBlob => {
            trackData.imageBlobUrl = URL.createObjectURL(imageBlob);
            console.info('queue | download lyrics');
            trackData.lyricsUrl = '/get_lyrics' + trackData.queryString;
            return fetch(new Request(trackData.lyricsUrl));
        }, throwErr)
        .then(response => {
            if (response.status == 200) {
                return response.json();
            } else {
                throw 'response code ' + response.status;
            }
        }, throwErr)
        .then(lyricsJson => {
            trackData.lyrics = lyricsJson;
            document.queue.push(trackData);
            updateQueueHtml();
            console.info("queue | done");
            if (onComplete !== undefined) {
                onComplete();
            }
        })
        .then(null, error => {
            console.warn('queue | error');
            console.warn(error);
            if (onComplete !== undefined) {
                onComplete();
            }
        });
}

function getTrackFromQueue() {
    // Get and remove first element from queue
    const track = document.queue.shift();
    updateQueueHtml();
    return track;
}

function escapeHtml(unescaped) {
    const p = document.createElement("p");
    p.textContent = unescaped;
    return p.innerHTML;
}

function removeFromQueue(index) {
    document.queue.splice(index, 1);
    updateQueueHtml();
    updateQueue();
}

function updateQueueHtml() {
    const trashBase64 = document.getElementById('trash-can-base64').innerText;

    let html = `
        <table class="queue-table">
            <tbody>`;
    let i = 0;
    for (const queuedTrack of document.queue) {
        html += '<tr>';
            html += '<td class="background-cover box" style="background-image: url(\'' + escapeHtml(queuedTrack.imageBlobUrl) + '\')">';
                html += '<div class="delete-overlay">'
                    html += '<div style="background-image: url(\'' + trashBase64 + '\')" class="icon" onclick="removeFromQueue(' + i + ')"></div>';
                html += '</div>'
            html += '</td>';
            html += '<td>' + queuedTrack.personDisplay + '</td>';
            html += '<td>' + escapeHtml(queuedTrack.displayName) + '</td>';
        html += '</tr>';
        i++;
    }

    let first = true;
    while (i < document.queueSize) {
        html += '<tr><td colspan="3" class="secondary downloading">';
        if (first) {
            first = false;
            html += '<span class="spinner" id="queue-spinner"></span>';
        }
        html += '</td></tr>';
        i++;
    }

    html += '</tbody></table>';
    const outerDiv = document.getElementById('queue');
    outerDiv.innerHTML = html;
}

function secondsToString(seconds) {
    // https://stackoverflow.com/a/25279399/4833737
    return new Date(1000 * seconds).toISOString().substring(14, 19);
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
                output.style.backgroundColor = json.code === 0 ? 'lightgreen' : 'pink';
            });
        } else {
            response.text().then(alert);
        }
    });
}

function switchLyrics() {
    document.getElementById('button-record-vinyl').style.display = '';
    document.getElementById('button-closed-captioning').style.display = 'none';
    document.getElementById('sidebar-lyrics').style.display = 'flex';
    document.getElementById('sidebar-album-covers').style.display = 'none';
}

function switchAlbumCover() {
    document.getElementById('button-record-vinyl').style.display = 'none';
    document.getElementById('button-closed-captioning').style.display = '';
    document.getElementById('sidebar-lyrics').style.display = 'none';
    document.getElementById('sidebar-album-covers').style.display = 'flex';
}

function initTrackList() {
    fetch(new Request('/track_list'))
        .then(response => response.json())
        .then(json => {
            document.trackList = json.persons
            searchTrackList();
        });
}

function queueAdd(id) {
    const button = document.getElementById(id);
    const trackData = {
        person: button.dataset.personDir,
        personDisplay: button.dataset.personDisplay,
        name: button.dataset.trackFile,
        displayName: button.dataset.trackDisplay,
    };
    downloadAndAddToQueue(trackData);
    document.getElementById('queue-overlay').style.display = 'none';
}

function searchTrackList() {
    if (document.trackList === undefined) {
        document.getElementById('track-list-output').textContent = 'Track list is still loading, please wait...';
        return;
    }

    const person = document.getElementById('track-list-person').value;
    const query = document.getElementById('track-list-query').value.trim().toLowerCase();

    let outputHtml = '';
    let i = 0;
    outer:
    for (const personJson of document.trackList) {
        if (person === 'everyone' || person === personJson.dir_name) {
            for (const track of personJson.tracks) {
                if (query === '' ||
                        track.file.toLowerCase().includes(query) ||
                        track.display.toLowerCase().includes(query)) {
                    outputHtml += ''
                        + '<button '
                        + 'id="queue-choice-' + i + '" '
                        + 'data-person-dir="' + escapeHtml(personJson.dir_name) + '" '
                        + 'data-person-display="' + escapeHtml(personJson.display_name) + '" '
                        + 'data-track-file="' + escapeHtml(track.file) + '" '
                        + 'data-track-display="' + escapeHtml(track.display) + '" '
                        + 'onclick="queueAdd(this.id);">'
                        + '[' + escapeHtml(personJson.display_name) + '] ' + escapeHtml(track.display)
                        + '</button><br>';
                }

                if (i > 10) {
                    outputHtml += '...en meer';
                    break outer;
                }

                i++;
            }

        }
    }

    document.getElementById('track-list-output').innerHTML = outputHtml;
}

// Audio normalisatie dingen gestolen met modificaties van:
// https://github.com/est31/js-audio-normalizer/blob/master/normalizer/normalizer.html

// var audioCtx = new AudioContext();

// function normalizedAudioElement(streamUrl) {
//     const audioElem = document.createElement('audio');
//     audioElem.onended = liedje;
//     audioElem.ontimeupdate = () => updateProgress(audioElem);

// 	var src = audioCtx.createMediaElementSource(audioElem);
// 	var gainNode = audioCtx.createGain();
// 	gainNode.gain.value = 0.1; // voor het geval er iets mis gaat willen we de gain laag hebben

// 	audioElem.addEventListener("play", function() {
// 		src.connect(gainNode);
// 		gainNode.connect(audioCtx.destination);
// 	}, true);
// 	audioElem.addEventListener("pause", function() {
// 		// disconnect the nodes on pause, otherwise all nodes always run
// 		src.disconnect(gainNode);
// 		gainNode.disconnect(audioCtx.destination);
// 	}, true);
// 	fetch(streamUrl)
// 		.then(res => res.blob())
//         .then(blob => {
//             // De functie die ik gestolen heb wil zelf de mp3 downloaden. Om te voorkomen
//             // dat de download 2 keer gebeurd, converteren we hier de response naar een blob
//             // en geven we die direct aan het audio element.
//             // Vervolgens krijgt de rest van de functie de blob als ArrayBuffer
//             const sourceElem = document.createElement('source');
//             sourceElem.src = URL.createObjectURL(blob);
//             audioElem.appendChild(sourceElem);
//             return blob.arrayBuffer();
//         })
// 		.then(buf => audioCtx.decodeAudioData(buf))
// 		.then(function(decodedData) {
// 			var decodedBuffer = decodedData.getChannelData(0);
// 			var sliceLen = Math.floor(decodedData.sampleRate * 0.05);
// 			var averages = [];
// 			var sum = 0.0;
// 			for (var i = 0; i < decodedBuffer.length; i++) {
// 				sum += decodedBuffer[i] ** 2;
// 				if (i % sliceLen === 0) {
// 					sum = Math.sqrt(sum / sliceLen);
// 					averages.push(sum);
// 					sum = 0;
// 				}
// 			}
// 			// Ascending sort of the averages array
// 			averages.sort(function(a, b) { return a - b; });
// 			// Take the average at the 95th percentile
// 			var a = averages[Math.floor(averages.length * 0.95)];

// 			var gain = 1.0 / a;
// 			gain = gain / 10.0;
//             console.log('Gain', gain)
// 			gainNode.gain.value = gain;

//             // Nu dat de gain aangepast is kan de audio afgespeeld worden
//             audioElem.play();
//             const songButton = document.getElementById('ff-button');
//             songButton.removeAttribute('disabled');
// 		});
//     return audioElem;
// }
