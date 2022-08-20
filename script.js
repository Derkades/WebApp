"use strict";

document.queue = [];
document.queueBusy = false;
document.queueSize = 4;

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById('button-backward-fast').addEventListener('click', () => seek(-30));
    document.getElementById('button-backward').addEventListener('click', () => seek(-5));
    document.getElementById('button-play').addEventListener('click', play);
    document.getElementById('button-pause').addEventListener('click', pause);
    document.getElementById('button-forward').addEventListener('click', () => seek(5));
    document.getElementById('button-forward-fast').addEventListener('click', () => seek(30));
    document.getElementById('button-forward-step').addEventListener('click', liedje);

    document.addEventListener('keydown', event => handleKey(event.key));

    updateQueueHtml();
    updateQueue();
    liedje();
    setInterval(showCorrectPlayPauseButton, 50);
});

function handleKey(key) {
    let elemId = null;
    const keyInt = parseInt(key);
    if (!isNaN(keyInt)) {
        if (keyInt === 1) {
            elemId = 'enable-CB';
        } else if (keyInt == 2) {
            elemId = 'enable-DK';
        } else if (keyInt === 3) {
            elemId = 'enable-JK';
        } else if (keyInt >= 4 && keyInt <= 9) {
            const guestBoxesElem = document.getElementById('guest-checkboxes');
            let index = 4;
            if (guestBoxesElem) {
                for (const child of guestBoxesElem.children) {
                    if (child.tagName !== "INPUT") {
                        continue;
                    }
                    if (index === keyInt) {
                        elemId = child.id;
                        break;
                    }
                    index++;
                }
            }
        }

        console.log('number key', keyInt, 'elemId', elemId);
        if (elemId !== null) {
            const elem = document.getElementById(elemId);
            elem.checked = !elem.checked;
        }
    } else if (key === 'p' || key === ' ') {
        playPause();
    } else if (key === 'ArrowRight' || key === 'f') {
        liedje();
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

    const audioElem = createAudioElement(track.audioUrl);
    replaceAudioElement(audioElem);

    replaceAlbumImages(track.imageUrl)

    // Replace 'currently playing' text
    const currentTrackElem = document.getElementById('current-track');
    const previousTrackElem = document.getElementById('previous-track');
    previousTrackElem.innerText = currentTrackElem.innerText;
    currentTrackElem.innerText = '[' + track.personDisplay + '] ' + track.name;

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

    ['CB', 'DK', 'JK'].forEach(function(person) {
        if (document.getElementById('enable-' + person).checked) {
            active.push(person);
        }
    });

    const guestBoxesElem = document.getElementById('guest-checkboxes');
    if (guestBoxesElem) {
        Array.from(guestBoxesElem.children).forEach(child => {
            if (child.tagName !== "INPUT") {
                return;
            }

            if (child.checked) {
                active.push(child.name);
            }
        });
    }

    return active;
}

function updateProgress(audioElem) {
    const current = secondsToString(Math.floor(audioElem.currentTime));
    const max = secondsToString(Math.floor(audioElem.duration));
    const percentage = (audioElem.currentTime / audioElem.duration) * 100;

    const timeElem = document.getElementById('progress-time');
    timeElem.innerText = current + ' / ' + max;

    const barElem = document.getElementById('progress-bar');
    barElem.style.width = percentage + '%';
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

function updateQueue() {
    if (document.queueBusy) {
        return;
    }

    let person;

    if (document.queue.length > 0) {
        const lastTrack = document.queue[document.queue.length - 1];
        const lastPerson = lastTrack.person;
        person = getNextPerson(lastPerson);
    } else {
        person = getNextPerson();
    }

    if (document.queue.length < document.queueSize) {
        downloadTrackToQueue(person);
    }
}

function downloadTrackToQueue(person) {
    document.queueBusy = true;
    console.log('updating queue, finding track...');
    fetch(new Request('/choose_track?person=' + encodeURIComponent(person)))
        .then(response => response.json())
        .then(data => {
            console.log('updating queue, downloading track...');

            const trackName = data.name;
            const streamUrl = '/get_track?person=' + encodeURIComponent(person) + '&track_name=' + encodeURIComponent(trackName);
            fetch(new Request(streamUrl))
                .then(response => response.blob())
                .then(audioBlob => {
                    console.log('updating queue, downloading album cover...');
                    const coverUrl = '/get_album_cover?song_title=' + encodeURIComponent(trackName);
                    fetch(new Request(coverUrl))
                        .then(response => response.blob())
                        .then(imageBlob => {
                            let personDisplay;
                            if (person.startsWith("Guest-")) {
                                personDisplay = person.substring('6');
                            } else {
                                personDisplay = person;
                            }

                            const trackData = {
                                person: person,
                                personDisplay: personDisplay,
                                name: trackName,
                                audioUrl: URL.createObjectURL(audioBlob),
                                imageUrl: URL.createObjectURL(imageBlob),
                            }

                            document.queue.push(trackData);
                            document.queueBusy = false;
                            console.log('updating queue, done.');
                            updateQueueHtml();
                            updateQueue();
                        });
                });
        });
}

// function clearQueue() {
//     if (document.queueBusy) {
//         setTimeout(clearQueue, 500);
//         return;
//     }

//     document.queue = [];
//     updateQueue();
// }

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
    let html = `
        <table class="queue-table">
            <tbody>`;
    let i = 0;
    for (const queuedTrack of document.queue) {
        html += '<tr>';
        html += '<td class="background-cover box" style="background-image: url(\'' + escapeHtml(queuedTrack.imageUrl) + '\')" onclick="removeFromQueue(' + i + ')"></td>';
        html += '<td>' + queuedTrack.personDisplay + '</td>';
        html += '<td>' + escapeHtml(queuedTrack.name) + '</td>';
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