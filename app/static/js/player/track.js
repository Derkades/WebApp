class Track {
    /** @type {string} */
    path;
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
    artistsUppercase; // for browse.js
    /** @type {string | null} */
    album;
    /** @type {string | null} */
    albumUppercase;
    /** @type {string | null} */
    albumArtist;
    /** @type {string | null} */
    albumArtistUppercase; // for browse.js
    /** @type {number | null} */
    year;
    /** @type {string} */
    searchString;

    constructor(playlistName, trackData) {
        this.path = trackData.path;
        this.playlistName = playlistName;
        this.duration = trackData.duration;
        this.tags = trackData.tags;
        this.title = trackData.title;
        this.artists = trackData.artists;
        if (this.artists) {
            this.artistsUppercase = this.artists.map(s => s.toUpperCase());
        }
        this.album = trackData.album;
        if (this.album) this.albumUppercase = this.album.toUpperCase()
        this.albumArtist = trackData.album_artist;
        if (this.albumArtist) this.albumArtistUppercase = this.albumArtist.toUpperCase();
        this.year = trackData.year;

        this.searchString = this.path;
        if (this.title) {
            this.searchString += this.title;
        }
        if (this.artists) {
            this.searchString += this.artists.join(' ');
        }
        if (this.album) {
            this.searchString += this.album;
        }
        if (this.albumArtist) {
            this.searchString += this.albumArtist;
        }
    };

    /**
     * @returns {Playlist}
     */
    playlist() {
        return music.playlists[this.playlistName];
    };

    /**
     * Get display HTML for this track
     * @param {boolean} showPlaylist
     * @returns {HTMLSpanElement}
     */
    displayHtml(showPlaylist = false) {
        const html = document.createElement('span');
        html.classList.add('track-display-html');

        if (this.artists !== null && this.title !== null) {
            let first = true;
            for (const artist of this.artists) {
                if (first) {
                    first = false;
                } else {
                    html.append(', ');
                }

                const artistHtml = document.createElement('a');
                artistHtml.textContent = artist;
                artistHtml.onclick = () => browse.browseArtist(artist);
                html.append(artistHtml);
            }

            html.append(' - ' + this.title);
        } else {
            const span = document.createElement('span');
            span.style.color = COLOR_MISSING_METADATA;
            span.textContent = this.path.substring(this.path.indexOf('/') + 1);
            html.append(span);
        }

        const secondary = document.createElement('span');
        secondary.classList.add('secondary');
        secondary.append(document.createElement('br'));
        html.append(secondary);

        if (showPlaylist) {
            const playlistHtml = document.createElement('a');
            playlistHtml.onclick = () => browse.browsePlaylist(this.playlistName);
            playlistHtml.textContent = this.playlistName;
            secondary.append(playlistHtml);
        }

        if (this.year || this.album) {
            if (showPlaylist) {
                secondary.append(', ');
            }

            if (this.album) {
                const albumHtml = document.createElement('a');
                albumHtml.onclick = () => browse.browseAlbum(this.album, this.albumArtist);
                if (this.albumArtist) {
                    albumHtml.textContent = this.albumArtist + ' - ' + this.album;
                } else {
                    albumHtml.textContent = this.album;
                }
                secondary.append(albumHtml);
                if (this.year) {
                    secondary.append(', ');
                }
            }

            if (this.year) {
                secondary.append(this.year);
            }

        }

        return html;
    };

    /**
     * Generates display text for this track
     * @param {boolean} showPlaylist
     * @returns {string}
     */
    displayText(showPlaylist = false) {
        let text = '';

        if (showPlaylist) {
            text += `${this.playlistName}: `
        }

        if (this.artists !== null && this.title !== null) {
            text += this.artists.join(', ');
            text += ' - ';
            text += this.title;
        } else {
            text += this.path.substring(this.path.indexOf('/') + 1);
        }

        return text;
    };

    /**
     * Download track data, and add to queue
     * @param {boolean} manual
     */
    async downloadAndAddToQueue(manual) {
        const audioType = document.getElementById('settings-audio-type').value;

        if (audioType.startsWith('webm') &&
                getAudioElement().canPlayType("audio/webm;codecs=opus") != "probably" &&
                getAudioElement().canPlayType("video/mp4;codecs=mp4a.40.2") == "probably") {
            audioType = "mp4_aac";
            alert("WEBM/OPUS audio not supported by your browser, audio quality has been set to MP4/AAC");
            document.getElementById('settings-audio-type').value = "mp4_aac";
            audioType = "mp4_aac";
        }

        const imageQuality = audioType == 'webm_opus_low' ? 'low' : 'high';
        const encodedPath = encodeURIComponent(this.path);

        const audioUrl = `/track/audio?path=${encodedPath}&type=${audioType}`;
        let audioUrlGetter;
        if (document.getElementById('settings-download-mode').value === 'download') {
            audioUrlGetter = async function() {
                // Get track audio
                const trackResponse = await fetch(audioUrl);
                checkResponseCode(trackResponse);
                const audioBlob = await trackResponse.blob();
                console.debug('track: downloaded audio');
                return URL.createObjectURL(audioBlob);
            };
        } else {
            audioUrlGetter = async function() {
                return audioUrl;
            }
        }

        const imageBlobUrlGetter = async function() {
            // Get cover image
            const meme = document.getElementById('settings-meme-mode').checked ? '1' : '0';
            const imageUrl = `/track/album_cover?path=${encodedPath}&quality=${imageQuality}&meme=${meme}`;
            const coverResponse = await fetch(imageUrl);
            checkResponseCode(coverResponse);
            const imageBlob = await coverResponse.blob();
            console.debug('track: downloaded album cover image');
            return URL.createObjectURL(imageBlob);
        };

        const lyricsGetter = async function() {
            // Get lyrics
            const lyricsResponse = await fetch(`/track/lyrics?path=${encodedPath}`);
            checkResponseCode(lyricsResponse);
            const lyricsJson = await lyricsResponse.json();
            console.debug('track: downloaded lyrics');
            return lyricsJson.found ? new Lyrics(lyricsJson.source, lyricsJson.html) : null;
        };

        // Resolve all, download in parallel
        const promises = Promise.all([audioUrlGetter(), imageBlobUrlGetter(), lyricsGetter()]);
        const [audioUrl2, imageBlobUrl, lyrics] = await promises;

        const queuedTrack = new QueuedTrack(this, audioUrl2, imageBlobUrl, lyrics);

        // Add track to queue and update HTML
        queue.add(queuedTrack, manual);
    };
};

class Lyrics {
    /** @type {string | null} */
    source;
    /** @type {string} */
    html;
    constructor(source, html) {
        this.source = source;
        this.html = html;
    };
};
