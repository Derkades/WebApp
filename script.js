function liedje() {
    const person = getNextPerson();
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
            const audioElem = document.createElement('audio');
            const sourceElem = document.createElement('source');
            sourceElem.setAttribute('src', streamUrl);
            audioElem.setAttribute('controls', '');
            audioElem.setAttribute('autoplay', '');
            audioElem.appendChild(sourceElem);
            audioDiv.innerHTML = '';
            audioDiv.appendChild(audioElem);
            audioElem.onended = liedje;

            // Replace album cover
            const albumCoverUrl = '/get_album_cover?song_title=' + encodeURIComponent(trackName);
            ['album-cover', 'bg-image'].forEach(id => {
                document.getElementById(id).style.backgroundImage = 'url("' + albumCoverUrl + '")';
            });

            // Replace 'currently playing' text
            const currentTitleElem = document.getElementById('current-song-title');
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

    // TODO extra person checkboxes

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

    const currentPersonElem = document.getElementById('current-song-person');
    currentPersonElem.innerText = person;

    document.currentPerson = person;

    return person;
}

document.addEventListener("DOMContentLoaded", function () {
    const songButton = document.getElementById('song-button');
    songButton.addEventListener("click", liedje);
});
