document.addEventListener("DOMContentLoaded", function () {
    const songButton = document.getElementById('song-button');
    songButton.addEventListener("click", liedje);
    liedje();
});

function liedje() {
    const person = getNextPerson();

    const currentPersonElem = document.getElementById('current-song-person');
    const previousPersonElem = document.getElementById('previous-song-person');
    previousPersonElem.innerText = currentPersonElem.innerText;
    currentPersonElem.innerText = person;

    const request = new Request('/choose_track?person=' + encodeURIComponent(person), {
        method: 'GET',
    });

    fetch(request).then(response => {
        response.json().then(data => {
            const trackName = data.name;
            const streamUrl = '/get_track?person=' + encodeURIComponent(person) + '&track_name=' + encodeURIComponent(trackName);

            // Replace audio stream
            // TODO volume van oude audio element overnemen voor nieuwe element
            const audioDiv = document.getElementById('audio');

            // Kies hier tussen streaming en normalized
            // const audioElem = streamingAudioElement(streamUrl);
            const audioElem = normalizedAudioElement(streamUrl);

            audioDiv.innerHTML = '';
            audioDiv.appendChild(audioElem);

            // Replace album cover
            const albumCoverUrl = '/get_album_cover?song_title=' + encodeURIComponent(trackName);
            ['album-cover', 'bg-image'].forEach(id => {
                document.getElementById(id).style.backgroundImage = 'url("' + albumCoverUrl + '")';
            });

            // Replace 'currently playing' text
            console.log('Now playing', trackName);
            console.log('Stream URL', streamUrl);
            const currentTitleElem = document.getElementById('current-song-title');
            const previousTitleElem = document.getElementById('previous-song-title');
            previousTitleElem.innerText = currentTitleElem.innerText;
            currentTitleElem.innerText = trackName;
        });
    });
}

function getActivePersons() {
    const active = [];

    ['CB', 'DK', 'JK'].forEach(function(person) {
        if (document.getElementById('enable-' + person).checked) {
            active.push(person);
        }
    });

    const guestBoxesElem = document.getElementById('guest-checkboxes');
    Array.from(guestBoxesElem.children).forEach(child => {
        if (child.tagName !== "INPUT") {
            return;
        }

        if (child.checked) {
            active.push(child.name);
        }
    });

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
        // TODO how to handle properly?
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

function streamingAudioElement(streamUrl) {
    const audioElem = document.createElement('audio');
    const sourceElem = document.createElement('source');
    sourceElem.setAttribute('src', streamUrl);
    audioElem.setAttribute('controls', '');
    audioElem.setAttribute('autoplay', '');
    audioElem.appendChild(sourceElem);
    audioElem.onended = liedje;
    return audioElem;
}

// Audio normalisatie dingen gestolen met modificaties van:
// https://github.com/est31/js-audio-normalizer/blob/master/normalizer/normalizer.html

var audioCtx = new AudioContext();

function normalizedAudioElement(streamUrl) {
	// var audioElem = document.getElementById(name + "-n");
    const audioElem = document.createElement('audio');
    audioElem.setAttribute('controls', '');
    audioElem.onended = liedje;
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
		});
    return audioElem;
}
