document.addEventListener('DOMContentLoaded', () => {
    /** @type {HTMLInputElement} */
    const spotifySubmit = document.getElementById('spotify-submit');
    /** @type {HTMLSelectElement} */
    const spotifyPlaylist = document.getElementById('spotify-playlist');
    /** @type {HTMLInputElement} */
    const spotifyUrl = document.getElementById('spotify-url');

    spotifySubmit.addEventListener('click', () => {
        const playlist = spotifyPlaylist.value;

        let url = spotifyUrl.value;

        if (!url.startsWith('https://open.spotify.com/playlist/')) {
            alert('invalid url');
            return;
        }

        url = url.substring('https://open.spotify.com/playlist/'.length);

        if (url.indexOf('?si') != -1) {
            url = url.substring(0, url.indexOf('?si'));
        }

        window.location = '/playlist/' + encodeURIComponent(playlist) + '/compare_spotify?playlist_id=' + encodeURIComponent(url);
    });
});
