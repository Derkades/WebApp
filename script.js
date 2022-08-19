"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const songButton = document.getElementById('ff-button');
    songButton.addEventListener("click", liedje);

    const ppButton = document.getElementById('pp-button');
    ppButton.addEventListener("click", playPause);

    document.addEventListener('keydown', event => handleKey(event.key));

    liedje();
});

function handleKey(key) {
    var elemId = null;
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
            var index = 4;
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
        const songButton = document.getElementById('ff-button');
        if (!songButton.hasAttribute('disabled')) {
            liedje();
        }
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

function playPause() {
    const audioElem = getAudioElement();
    if (audioElem.paused) {
        audioElem.play();
    } else {
        audioElem.pause();
    }
}

function liedje() {
    document.getElementById('ff-button').setAttribute('disabled', '');

    const person = getNextPerson();

    const request = new Request('/choose_track?person=' + encodeURIComponent(person),
                                { method: 'GET'});

    fetch(request)
        .then(response => response.json())
        .then(data => {
            const trackName = data.name;
            const streamUrl = '/get_track?person=' + encodeURIComponent(person) + '&track_name=' + encodeURIComponent(trackName);

            console.log('Now playing', trackName, streamUrl);

            // Kies hier tussen streaming en normalized
            replaceAudioElement(streamingAudioElement(streamUrl));
            // replaceAudioElement(normalizedAudioElement(streamUrl));

            updateAlbumCover(trackName);

            // Replace 'currently playing' text
            const currentTrackElem = document.getElementById('current-track');
            const previousTrackElem = document.getElementById('previous-track');
            previousTrackElem.innerText = currentTrackElem.innerText;
            currentTrackElem.innerText = '[' + person + '] ' + trackName;
        });
}

function updateAlbumCover(trackName) {
    const albumCoverUrl = '/get_album_cover?song_title=' + encodeURIComponent(trackName);
    const image = new Image();
    image.src = albumCoverUrl;
    image.onload = () => {
        ['album-cover', 'bg-image'].forEach(id => {
            document.getElementById(id).style.backgroundImage = 'url("' + albumCoverUrl + '")';
        });
    }
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

function choice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function getNextPerson() {
    const active = getActivePersons();

    var person;

    if (active.length === 0) {
        // No one is selected
        // eigenlijk zou er een error moeten komen, maar voor nu kiezen we DK
        person = "DK";
    } else if (document.currentPerson === undefined) {
        // No person chosen yet, choose random person
        person = choice(active);
    } else {
        const currentIndex = active.indexOf(document.currentPerson);
        if (currentIndex === -1) {
            // Current person is no longer active, we don't know the logical next person
            // Choose random person
            person = choice(active);
        } else {
            // Choose next person in list, wrapping around if at the end
            person = active[(currentIndex + 1) % active.length];
        }
    }

    document.currentPerson = person;

    return person;
}

function updateProgress(audioElem) {
    const current = Math.floor(audioElem.currentTime);
    const max = Math.floor(audioElem.duration);
    const percentage = (audioElem.currentTime / audioElem.duration) * 100;

    const timeElem = document.getElementById('progress-time');
    timeElem.innerText = current + ' / ' + max;

    const barElem = document.getElementById('progress-bar');
    barElem.style.width = percentage + '%';
}

function streamingAudioElement(streamUrl) {
    const audioElem = document.createElement('audio');
    const sourceElem = document.createElement('source');
    sourceElem.setAttribute('src', streamUrl);
    audioElem.setAttribute('autoplay', '');
    audioElem.appendChild(sourceElem);
    audioElem.onended = liedje;
    audioElem.ontimeupdate = () => updateProgress(audioElem);
    const songButton = document.getElementById('ff-button');
    songButton.removeAttribute('disabled');
    return audioElem;
}

// Audio normalisatie dingen gestolen met modificaties van:
// https://github.com/est31/js-audio-normalizer/blob/master/normalizer/normalizer.html

var audioCtx = new AudioContext();

function normalizedAudioElement(streamUrl) {
    const audioElem = document.createElement('audio');
    audioElem.onended = liedje;
    audioElem.ontimeupdate = () => updateProgress(audioElem);

	var src = audioCtx.createMediaElementSource(audioElem);
	var gainNode = audioCtx.createGain();
	gainNode.gain.value = 0.1; // voor het geval er iets mis gaat willen we de gain laag hebben

	audioElem.addEventListener("play", function() {
		src.connect(gainNode);
		gainNode.connect(audioCtx.destination);
	}, true);
	audioElem.addEventListener("pause", function() {
		// disconnect the nodes on pause, otherwise all nodes always run
		src.disconnect(gainNode);
		gainNode.disconnect(audioCtx.destination);
	}, true);
	fetch(streamUrl)
		.then(res => res.blob())
        .then(blob => {
            // De functie die ik gestolen heb wil zelf de mp3 downloaden. Om te voorkomen
            // dat de download 2 keer gebeurd, converteren we hier de response naar een blob
            // en geven we die direct aan het audio element.
            // Vervolgens krijgt de rest van de functie de blob als ArrayBuffer
            const sourceElem = document.createElement('source');
            sourceElem.src = URL.createObjectURL(blob);
            audioElem.appendChild(sourceElem);
            return blob.arrayBuffer();
        })
		.then(buf => audioCtx.decodeAudioData(buf))
		.then(function(decodedData) {
			var decodedBuffer = decodedData.getChannelData(0);
			var sliceLen = Math.floor(decodedData.sampleRate * 0.05);
			var averages = [];
			var sum = 0.0;
			for (var i = 0; i < decodedBuffer.length; i++) {
				sum += decodedBuffer[i] ** 2;
				if (i % sliceLen === 0) {
					sum = Math.sqrt(sum / sliceLen);
					averages.push(sum);
					sum = 0;
				}
			}
			// Ascending sort of the averages array
			averages.sort(function(a, b) { return a - b; });
			// Take the average at the 95th percentile
			var a = averages[Math.floor(averages.length * 0.95)];

			var gain = 1.0 / a;
			gain = gain / 10.0;
            console.log('Gain', gain)
			gainNode.gain.value = gain;

            // Nu dat de gain aangepast is kan de audio afgespeeld worden
            audioElem.play();
            const songButton = document.getElementById('ff-button');
            songButton.removeAttribute('disabled');
		});
    return audioElem;
}
