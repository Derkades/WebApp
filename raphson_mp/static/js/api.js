"use strict";

// Common JavaScript interface to API, to be used by the music player and other pages.
// Scripts using this API must implement a getCsrfToken() function that returns a usable CSRF token as a string.

class Music {
    /** @type {string} */
    #playerId;
    /** @type {Array<Playlist>} */
    #playlists;

    constructor() {
        this.#playerId = uuidv4();
    }

    /**
     * @returns {Promise<Array<Playlist>>}
     */
    async playlists() {
        await navigator.locks.request("api_playlists", async lock => {
            if (this.#playlists == undefined) {
                const response = await fetch('/playlist/list');
                checkResponseCode(response);
                const json = await response.json();
                this.#playlists = [];
                for (const playlistObj of json) {
                    this.#playlists.push(new Playlist(playlistObj));
                }
            }
        });

        return this.#playlists;
    }

    /**
     * @param {string} name
     * @returns {Promise<Playlist>}
     */
    async playlist(name) {
        const playlists = await this.playlists();
        for (const playlist of playlists) {
            if (playlist.name == name) {
                return playlist;
            }
        }
        return null;
    }

    /**
     * @param {object} json
     * @returns {Promise<Array<Track>>}
     */
    #tracksFromJson(json) {
        const tracks = [];
        for (const trackObj of json) {
            tracks.push(new Track(trackObj));
        }
        return tracks;
    }

    /**
     * @param {object} filters with key = playlist, artist, album_artist, album, etc.
     * @returns {Promise<Array<Track>>}
     */
    async filter(filters) {
        const encodedFilters = [];
        for (const filter in filters) {
            encodedFilters.push(filter + '=' + encodeURIComponent(filters[filter]));
        }
        const response = await fetch('/track/filter?' + encodedFilters.join('&'));
        checkResponseCode(response);
        const json = await response.json();
        return this.#tracksFromJson(json.tracks);
    }

    /**
     * @param {string} query FTS5 search query
     * @returns {Promise<Array<Track>>}
     */
    async search(query) {
        const response = await fetch('/track/search?query=' + encodeURIComponent(query));
        checkResponseCode(response);
        const json = await response.json();
        return this.#tracksFromJson(json.tracks);
    }

    /**
     * @param {string} path
     * @returns {Promise<Track>}
     */
    async track(path) {
        const response = await fetch(`/track/info${encodeURIComponent(path)}/info`);
        checkResponseCode(response);
        return new Track(await response.json());
    }

    /**
     * @returns {Promise<Array<string>>}
     */
    async tags() {
        const response = await fetch('/track/tags');
        checkResponseCode(response);
        return await response.json();
    }

    /**
     * Send signal to music player that this track is currently playing. Must be sent at least
     * every 60 seconds, more frequently is recommended if progress data is included.
     * @param {Track} track
     * @param {boolean} paused
     * @param {number} currentTime
     */
    async nowPlaying(track, paused, currentTime) {
        const data = {
            player_id: this.#playerId,
            track: track.path,
            paused: paused,
            progress: Math.round((currentTime / track.duration) * 100),
        };
        await jsonPost('/activity/now_playing', data);
    }

    /**
     * @param {track} track
     */
    async played(track, startTimestamp) {
        const data = {
            track: track.path,
            timestamp: startTimestamp,
        }
        await jsonPost('/activity/played', data);
    }
}

const music = new Music();

class Playlist {
    /** @type {string} */
    name;
    /** @type {number} */
    trackCount;
    /** @type {boolean} */
    favorite;
    /** @type {boolean} */
    write;

    /**
     * @param {Object.<string, string|boolean|number} objectFromApi
     */
    constructor(objectFromApi) {
        this.name = objectFromApi.name;
        this.trackCount = objectFromApi.track_count;
        this.favorite = objectFromApi.favorite;
        this.write = objectFromApi.write;
    }

    async chooseRandomTrack(requireMetadata, tagFilter) {
        const chooseResponse = await jsonPost('/playlist/' + encodeURIComponent(this.name) + '/choose_track', {'require_metadata': requireMetadata, ...tagFilter});
        const trackData = await chooseResponse.json();
        console.info('api: chosen track', trackData.path);
        return new Track(trackData);
    }
}

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
    /** @type {string | null} */
    album;
    /** @type {string | null} */
    albumArtist;
    /** @type {number | null} */
    year;

    constructor(trackData) {
        this.#updateLocalVariablesFromTrackDataResponse(trackData);
    };

    #updateLocalVariablesFromTrackDataResponse(trackData) {
        this.path = trackData.path;
        this.playlistName = trackData.playlist;
        this.duration = trackData.duration;
        this.tags = trackData.tags;
        this.title = trackData.title;
        this.artists = trackData.artists;
        this.album = trackData.album;
        this.albumArtist = trackData.album_artist;
        this.year = trackData.year;
    }

    // TODO uses player-specific code, does not belong in api.js
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
    displayText(showPlaylist = false, showAlbum = false) {
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

        if (this.album && showAlbum) {
            text += ` (${this.album}`;
            if (this.year) {
                text += `, ${this.year})`;
            } else {
                text += ')';
            }
        } else if (this.year) {
            text += ` (${this.year})`;
        }

        return text;
    };

    /**
     * @param {string} audioType
     * @param {boolean} stream
     * @returns {Promise<string>} URL
     */
    async getAudio(audioType, stream) {
        const audioUrl = `/track/${encodeURIComponent(this.path)}/audio?type=${audioType}`;
        if (stream) {
            return audioUrl;
        } else {
            const trackResponse = await fetch(audioUrl);
            checkResponseCode(trackResponse);
            const audioBlob = await trackResponse.blob();
            console.debug('track: downloaded audio', audioUrl);
            return URL.createObjectURL(audioBlob);
        }
    }

    /**
     *
     * @param {string} imageQuality 'low' or 'high'
     * @param {boolean} stream
     * @param {boolean} memeCover
     * @returns {Promise<string>} URL
     */
    async getCover(imageQuality, stream=false, memeCover=false) {
        const imageUrl = `/track/${encodeURIComponent(this.path)}/cover?quality=${imageQuality}&meme=${memeCover ? 1 : 0}`;
        if (stream) {
            return imageUrl;
        } else {
            const coverResponse = await fetch(imageUrl);
            checkResponseCode(coverResponse);
            const imageBlob = await coverResponse.blob();
            console.debug('track: downloaded image', imageUrl);
            return URL.createObjectURL(imageBlob);
        }
    }

    /**
     * @returns {Promise<Lyrics|null>}
     */
    async getLyrics() {
        const lyricsUrl = `/track/${encodeURIComponent(this.path)}/lyrics`;
        const lyricsResponse = await fetch(lyricsUrl);
        checkResponseCode(lyricsResponse);
        const lyricsJson = await lyricsResponse.json();
        console.debug('track: downloaded lyrics', lyricsUrl);
        return lyricsJson.lyrics ? new Lyrics(lyricsJson.source_url, lyricsJson.lyrics) : null;
    }

    /**
     * @param {string} audioType
     * @param {boolean} stream
     * @param {boolean} memeCover
     * @returns {Promise<DownloadedTrack>}
     */
    async download(audioType='webm_opus_high', stream=false, memeCover=false) {
        // Download audio, cover, lyrics in parallel
        const promises = [
            this.getAudio(audioType, stream),
            this.getCover(audioType == 'webm_opus_low' ? 'low' : 'high', stream, memeCover),
            this.getLyrics(),
        ];
        return new DownloadedTrack(this, ...(await Promise.all(promises)));
    }

    async delete() {
        const oldName = this.path.split('/').pop();
        const newName = '.trash.' + oldName;
        await jsonPost('/files/rename', {path: this.path, new_name: newName});
    }

    async dislike() {
        jsonPost('/dislikes/add', {track: this.path});
    }

    /**
     * Updates track metadata by sending current metadata of this object to the server.
     */
    async saveMetadata() {
        const payload = {
            title: this.title,
            album: this.album,
            artists: this.artists,
            album_artist: this.albumArtist,
            tags: this.tags,
            year: this.year,
        };

        await jsonPost(`/track/${encodeURIComponent(this.path)}/update_metadata`, payload);
    }

    async copyTo(playlistName) {
        await jsonPost('/player/copy_track', {track: this.path, playlist: playlistName});
    }

    async refresh() {
        const response = await fetch(`/track/info${encodeURIComponent(path)}/info`);
        checkResponseCode(response);
        this.#updateLocalVariablesFromTrackDataResponse(await response.json());
    }
}

class DownloadedTrack {
    /**
     * @type {Track|null} Null for virtual tracks, like news
     */
    track;
    /**
     * @type {string}
     */
    audioUrl;
    /**
     * @type {string}
     */
    imageUrl;
    /**
     * @type {Lyrics|null}
     */
    lyrics;

    /**
     *
     * @param {Track|null} track
     * @param {string} audioUrl
     * @param {string} imageUrl
     * @param {Lyrics|null} lyrics
     */
    constructor(track, audioUrl, imageUrl, lyrics) {
        this.track = track;
        this.audioUrl = audioUrl;
        this.imageUrl = imageUrl;
        this.lyrics = lyrics;
    }

    revokeObjects() {
        URL.revokeObjectURL(this.audioUrl);
        URL.revokeObjectURL(this.imageUrl);
    }
}

class Lyrics {
    /** @type {string | null} */
    source;
    /** @type {string} */
    lyrics;
    constructor(source, lyrics) {
        this.source = source;
        this.lyrics = lyrics;
    };
};

/**
 * @param {string} url
 * @param {object} postDataObject
 * @returns {Promise<Response>}
 */
async function jsonPost(url, postDataObject, checkError = true) {
    postDataObject.csrf = getCsrfToken();
    const options = {
        method: 'POST',
        body: JSON.stringify(postDataObject),
        headers: new Headers({
            'Content-Type': 'application/json'
        }),
    };
    const response = await fetch(new Request(url, options));
    if (checkError) {
        checkResponseCode(response);
    }
    return response;
}

async function jsonGet(url, checkError = true) {
    const options = {
        headers: new Headers({
            'Accept': 'application/json'
        }),
    };
    const response = await fetch(new Request(url, options));
    if (checkError) {
        checkResponseCode(response);
    }
    return await response.json();
}
