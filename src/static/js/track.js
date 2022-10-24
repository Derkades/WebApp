class Track {
    trackData;
    path;
    display;
    displayFile;
    playlistPath;
    playlistDisplay;
    duration;
    tags;
    title;
    artists;
    album;
    albumArist;
    albumIndex;
    year;

    constructor(trackData) {
        this.trackData = trackData;
        this.path = trackData.path;
        this.display = trackData.display;
        this.displayFile = trackData.display_file;
        this.playlistPath = trackData.playlist;
        this.playlistDisplay = trackData.playlist_display;
        this.duration = trackData.duration;
        this.tags = trackData.tags;
        this.title = trackData.title;
        this.artists = trackData.artists;
        this.album = trackData.album;
        this.albumArtist = trackData.album_artist;
        this.albumIndex = trackData.album_index;
        this.year = trackData.year;
    };

    displayHtml(showPlaylist = false) {
        const html = document.createElement('span');
        html.classList.add('track-display-html');

        if (showPlaylist) {
            const playlistHtml = document.createElement('a');
            playlistHtml.onclick = () => browse.browsePlaylist(this.playlistPath);
            playlistHtml.textContent = this.playlistDisplay;
            html.append(playlistHtml, ': ');
        }

        if (this.artists !== null && this.title !== null) {
            let first = true;
            for (const artist of this.artists) {
                if (first) {
                    first = false;
                } else {
                    html.append(' & ');
                }

                const artistHtml = document.createElement('a');
                artistHtml.textContent = artist;
                artistHtml.onclick = () => browse.browseArtist(artist);
                html.append(artistHtml);
            }

            html.append(' - ');

            let titleHtml;
            if (this.album !== null) {
                titleHtml = document.createElement('a');;
                titleHtml.onclick = () => browse.browseAlbum(this.album, this.albumArtist);
            } else {
                titleHtml = document.createElement('span');
            }
            titleHtml.textContent = this.title;
            html.append(titleHtml);

            if (this.year !== null) {
                html.append(' [' + this.year + ']');
            }
        } else {
            // Use half-decent display name generated from file name by python backend
            html.append(this.displayFile + ' ~');
        }
        return html;
    };

    static findTrackByPath(path) {
        for (const track of state.tracks) {
            if (track.path === path) {
                return track;
            }
        }
        return null;
    };

    static async updateLocalTrackList() {
        console.info('Requesting track list');
        const response = await fetch('/track_list');
        const json = await response.json();

        state.playlists = json.playlists;
        state.mainPlaylists = [];
        state.guestPlaylists = [];
        for (const dir_name in state.playlists) {
            // TODO sort alphabetically by display name
            const playlist = state.playlists[dir_name];
            if (playlist.guest) {
                state.guestPlaylists.push(playlist);
            } else {
                state.mainPlaylists.push(playlist);
            }
        }
        state.tracks = json.tracks.map(trackData => new Track(trackData));

        hideLoadingOverlay();

        // Update HTML depending on state.playlists and state.tracks
        updatePlaylistCheckboxHtml();
        browse.updateCurrentView();
        createPlaylistDropdowns();
        updateTagCheckboxes();
    };

    static async scanPlaylist(playlist) {
        console.info('Scanning playlist: ' + playlist);
        return jsonPost('/scan_music', {playlist: playlist});
    };

    async downloadAndAddToQueue(top = false) {
        const encodedQuality = encodeURIComponent(document.getElementById('settings-audio-quality').value);
        const encodedPath = encodeURIComponent(this.path);
        const encodedCsrf = encodeURIComponent(getCsrfToken());

        // Get track audio
        console.info('queue | download audio');
        const trackResponse = await fetch('/get_track?path=' + encodedPath + '&quality=' + encodedQuality + '&csrf=' + encodedCsrf);
        checkResponseCode(trackResponse);
        const audioBlob = await trackResponse.blob();
        const audioBlobUrl = URL.createObjectURL(audioBlob);

        let imageBlobUrl;

        // Get cover image
        if (encodedQuality === 'verylow') {
            console.info('queue | using raphson image to save data');
            imageBlobUrl = '/raphson';
        } else {
            console.info('queue | download album cover image');
            const meme = document.getElementById('settings-meme-mode').checked ? '1' : '0';
            const imageUrl = '/get_album_cover?path=' + encodedPath + '&quality=' + encodedQuality + '&meme=' + meme + '&csrf=' + encodedCsrf;
            const coverResponse = await fetch(imageUrl);
            checkResponseCode(coverResponse);
            const imageBlob = await coverResponse.blob();
            imageBlobUrl = URL.createObjectURL(imageBlob);
        }

        let lyrics;

        // Get lyrics
        if (encodedQuality === 'verylow') {
            lyrics = new Lyrics(true, null, '<i>Lyrics were not downloaded to save data</i>');
        } else {
            console.info('queue | download lyrics');
            const lyricsResponse = await fetch('/get_lyrics?path=' + encodedPath + '&csrf=' + encodedCsrf);
            checkResponseCode(lyricsResponse);
            const lyricsJson = await lyricsResponse.json();
            lyrics = new Lyrics(lyricsJson.found, lyricsJson.source, lyricsJson.html);
        }

        const queuedTrack = new QueuedTrack(this.trackData, audioBlobUrl, imageBlobUrl, lyrics);

        // Add track to queue and update HTML
        queue.add(queuedTrack, top);
        console.info("queue | done");
    };
};

class QueuedTrack extends Track {
    audioBlobUrl;
    imageBlobUrl;
    lyrics;
    constructor(trackData, audioBlobUrl, imageBlobUrl, lyrics) {
        super(trackData);
        this.audioBlobUrl = audioBlobUrl;
        this.imageBlobUrl = imageBlobUrl;
        this.lyrics = lyrics;
    };
};

class Lyrics {
    found;
    source;
    html;
    constructor(found, source = null, html = null) {
        this.found = found;
        this.source = source;
        this.html = html;
    };
};
