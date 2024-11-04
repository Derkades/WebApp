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
        const response = await fetch('/tracks/filter?' + encodedFilters.join('&'));
        checkResponseCode(response);
        const json = await response.json();
        return this.#tracksFromJson(json.tracks);
    }

    /**
     * @param {string} query FTS5 search query
     * @returns {Promise<Array<Track>>}
     */
    async search(query) {
        const response = await fetch('/tracks/search?query=' + encodeURIComponent(query));
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
        const response = await fetch('/tracks/tags');
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

    /**
     * @param {string} url
     * @returns {Promise<DownloadedTrack>}
     */
    async downloadTrackFromWeb(url) {
        const audioResponse = await fetch('/download/ephemeral?url=' + encodeURIComponent(url));
        checkResponseCode(audioResponse);
        const audio = URL.createObjectURL(await audioResponse.blob());
        const image = '/static/img/raphson_small.webp';
        return new DownloadedTrack(null, audio, image, null);
    }

    /**
     * @returns {Promise<DownloadedTrack>}
     */
    async downloadNews() {
        const audioResponse = await fetch('/news/audio');
        checkResponseCode(audioResponse);
        const audioBlob = URL.createObjectURL(await audioResponse.blob());

        const imageUrl = '/static/img/raphson.png';

        return new DownloadedTrack(null, audioBlob, imageUrl, null);
    }

    /**
     * @param {Playlist} playlist Playlist
     * @param {number} index Hotkey number, set to >=10 to not assign a hotkey
     * @param {boolean} defaultChecked Whether checkbox should be checked
     * @returns {HTMLSpanElement}
     */
    #createPlaylistCheckbox(playlist, index, defaultChecked) {
        const input = document.createElement("input");
        input.type = 'checkbox';
        input.dataset.playlist = playlist.name;
        input.checked = defaultChecked;

        const sup = document.createElement('sup');
        if (index < 10) { // Assume number keys higher than 9 don't exist
            sup.textContent = index;
        }

        const trackCount = document.createElement('span');
        trackCount.classList.add('secondary', 'small');
        trackCount.textContent = ' ' + playlist.trackCount;

        const label = document.createElement("label");
        label.htmlFor = "checkbox-" + playlist.name;
        label.textContent = playlist.name;
        label.replaceChildren(playlist.name, sup, trackCount);

        const span = document.createElement("span");
        span.classList.add("checkbox-with-label");
        span.replaceChildren(input, label);

        return span;
    }

    /**
     * @returns {Promise<HTMLDivElement>}
     */
    async getPlaylistCheckboxes() {
        let index = 1;
        const mainDiv = document.createElement('div');
        const otherDiv = document.createElement('div');
        otherDiv.style.maxHeight = '20vh';
        otherDiv.style.overflowY = 'auto';

        for (const playlist of await this.playlists()) {
            if (playlist.favorite) {
                mainDiv.appendChild(this.#createPlaylistCheckbox(playlist, index++, true));
            } else {
                otherDiv.appendChild(this.#createPlaylistCheckbox(playlist, 10, false));
            }
        }

        const parent = document.createElement('div');
        parent.replaceChildren(mainDiv, otherDiv);
        return parent;
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

/**
 * Metadata suggested by AcoustID
 */
class SuggestedMetadata {
    /** @type {string} */
    id;
    /** @type {string} */
    title;
    /** @type {Array<string>} */
    artists;
    /** @type {string} */
    album;
    /** @type {string} */
    albumArtist;
    /** @type {number | null} */
    year;
    /** @type {string} */
    releaseType;
    /** @type {string} */
    packaging;

    constructor(metaObj) {
        this.id = metaObj.id;
        this.title = metaObj.title;
        this.artists = metaObj.artists;
        this.album = metaObj.album;
        this.albumArtist = metaObj.album_artist;
        this.year = metaObj.year;
        this.releaseType = metaObj.release_type;
        this.packaging = metaObj.packaging;
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
    /** @type {string | null} */
    video;

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
        this.video = trackData.video;
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
        secondary.classList.add('secondary', 'small');
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
        const lyricsUrl = `/track/${encodeURIComponent(this.path)}/lyrics2`;
        const lyricsResponse = await fetch(lyricsUrl);
        checkResponseCode(lyricsResponse);
        const lyricsJson = await lyricsResponse.json();
        console.debug('track: downloaded lyrics', lyricsUrl);
        switch(lyricsJson.type) {
            case "none":
                return null;
            case "synced":
                const lines = [];
                for (const line of lyricsJson.text) {
                    lines.push(new LyricsLine(line.start_time, line.text));
                }
                return new TimeSyncedLyrics(lyricsJson.source, lines);
            case "plain":
                return new PlainLyrics(lyricsJson.source, lyricsJson.text);
        }
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

    /**
     * Copy track to other playlist
     * @param {string} playlistName
     * @returns {Promise<void>}
     */
    async copyTo(playlistName) {
        await jsonPost('/player/copy_track', {track: this.path, playlist: playlistName});
    }

    async refresh() {
        const json = await jsonGet(`/track/${encodeURIComponent(this.path)}/info`);
        this.#updateLocalVariablesFromTrackDataResponse(json);
    }

    /**
     * Look up metadata for this track using the AcoustID service
     * @returns {Promise<Array<SuggestedMetadata>>}
     */
    async acoustid() {
        const json = await jsonGet(`/track/${encodeURIComponent(this.path)}/acoustid`)
        const array = [];
        for (const meta of json) {
            array.push(new SuggestedMetadata(meta));
        }
        return array;
    }

    getVideoURL() {
        return `/track/${encodeURIComponent(this.path)}/video`
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
        // audioUrl and imageUrl are not always object URLs. If they are not, revokeObjectURL does not raise an error.
        URL.revokeObjectURL(this.audioUrl);
        URL.revokeObjectURL(this.imageUrl);
    }
}

class Lyrics {
    /** @type {string | null} */
    source;
    constructor(source) {
        this.source = source;
    };
};

class PlainLyrics extends Lyrics {
    /** @type {string} */
    text;
    constructor(source, text) {
        super(source)
        this.text = text;
    };
};

class LyricsLine {
    /** @type {number} */
    startTime;
    /** @type {string} */
    text;
    constructor(startTime, text) {
        this.startTime = startTime;
        this.text = text;
    }
}

class TimeSyncedLyrics extends Lyrics {
    /** @type {Array<LyricsLine>} */
    text;
    constructor(source, text) {
        super(source);
        this.text = text;
    };

    /**
     * @returns {string}
     */
    asPlainText() {
        const lines = [];
        for (const line of this.text) {
            lines.push(line.text);
        }
        return lines.join('\n');
    }

    /**
     * @param {number} currentTime
     * @returns {number}
     */
    currentLine(currentTime) {
        currentTime += 0.5; // go to next line slightly earlier, to give the user time to read
        // current line is the last line where currentTime is after the line start time
        for (let i = 0; i < this.text.length; i++) {
            if (currentTime < this.text[i].startTime) {
                return i - 1;
            }
        }
        return this.text.length - 1;
    }
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
