class Track {
    /** @type {object} */
    trackData;
    /** @type {string} */
    path;
    /** @type {string} */
    display;
    /** @type {string} */
    playlistName;
    /** @type {number} */
    duration;
    /** @type {Array<string>} */
    tags;
    /** @type {string | null} */
    title;
    /** @type {Array<string> | null} */
    artists;
    /** @type {Array<string> | null} */
    artistsUppercase;
    /** @type {string | null} */
    album;
    /** @type {string | null} */
    albumUppercase;
    /** @type {string | null} */
    albumArtist;
    /** @type {string | null} */
    albumArtistUppercase;
    /** @type {number | null} */
    year;

    constructor(playlistName, trackData) {
        this.trackData = trackData;
        this.path = trackData.path;
        this.display = trackData.display;
        this.playlistName = playlistName;
        this.duration = trackData.duration;
        this.tags = trackData.tags;
        this.title = trackData.title;
        this.artists = trackData.artists;
        if (this.artists) this.artistsUppercase = this.artists.map(s => s.toUpperCase());
        this.album = trackData.album;
        if (this.album) this.albumUppercase = this.album.toUpperCase()
        this.albumArtist = trackData.album_artist;
        if (this.albumArtist) this.albumArtistUppercase = this.albumArtist.toUpperCase();
        this.year = trackData.year;
    };

    /**
     * @returns {Playlist}
     */
    playlist() {
        return state.playlists[this.playlistName];
    };

    /**
     * Get display HTML for this track
     * @param {boolean} showPlaylist
     * @returns {HTMLSpanElement}
     */
    displayHtml(showPlaylist = false) {
        const html = document.createElement('span');
        html.classList.add('track-display-html');

        if (showPlaylist) {
            const playlistHtml = document.createElement('a');
            playlistHtml.onclick = () => browse.browsePlaylist(this.playlistName);
            playlistHtml.textContent = this.playlistName;
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
                html.append(` [${this.year}]`);
            }
        } else {
            // Use half-decent display name generated from file name by python backend
            html.append(this.display);
        }
        return html;
    };

    static async updateLocalTrackList() {
        console.info('downloading track list');
        const response = await fetch('/track_list');
        const json = await response.json();

        state.playlists = {};
        state.tracks = {};
        for (const playlistObj of json.playlists) {
            state.playlists[playlistObj.name] = new Playlist(playlistObj);;
            for (const trackObj of playlistObj.tracks) {
                state.tracks[trackObj.path] = new Track(playlistObj.name, trackObj);
            }
        }

        eventBus.publish(MusicEvent.TRACK_LIST_CHANGE);
    };

    async downloadAndAddToQueue(top = false) {
        const encodedAudioType = encodeURIComponent(document.getElementById('settings-audio-type').value);
        const imageQuality = document.getElementById('settings-audio-type').value == 'webm_opus_low' ? 'low' : 'high';
        const encodedPath = encodeURIComponent(this.path);

        const audioBlobUrlGetter = async function() {
            // Get track audio
            console.debug('download audio');
            const trackResponse = await fetch(`/get_track?path=${encodedPath}&type=${encodedAudioType}`);
            checkResponseCode(trackResponse);
            const audioBlob = await trackResponse.blob();
            return URL.createObjectURL(audioBlob);
        };

        const imageBlobUrlGetter = async function() {
            // Get cover image
            console.debug('download album cover image');
            const meme = document.getElementById('settings-meme-mode').checked ? '1' : '0';
            const imageUrl = `/get_album_cover?path=${encodedPath}&quality=${imageQuality}&meme=${meme}`;
            const coverResponse = await fetch(imageUrl);
            checkResponseCode(coverResponse);
            const imageBlob = await coverResponse.blob();
            return URL.createObjectURL(imageBlob);
        };

        const lyricsGetter = async function() {
            // Get lyrics
            console.debug('download lyrics');
            const lyricsResponse = await fetch(`/get_lyrics?path=${encodedPath}`);
            checkResponseCode(lyricsResponse);
            const lyricsJson = await lyricsResponse.json();
            return new Lyrics(lyricsJson.found, lyricsJson.source, lyricsJson.html);
        };

        // Resolve all, download in parallel
        const promises = Promise.all([audioBlobUrlGetter(), imageBlobUrlGetter(), lyricsGetter()]);
        const [audioBlobUrl, imageBlobUrl, lyrics] = await promises;

        const queuedTrack = new QueuedTrack(this, audioBlobUrl, imageBlobUrl, lyrics);

        // Add track to queue and update HTML
        queue.add(queuedTrack, top);
    };
};

function initTrackList() {
    Track.updateLocalTrackList().catch(err => {
        console.warn('track list error', err);
        setTimeout(initTrackList, 1000);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initTrackList();
    setInterval(initTrackList, 15*60*1000);
});

class Lyrics {
    /** @type {boolean} */
    found;
    /** @type {string | null} */
    source;
    /** @type {string | null} */
    html;
    constructor(found, source = null, html = null) {
        this.found = found;
        this.source = source;
        this.html = html;
    };
};
