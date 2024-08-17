// Common JavaScript interface to API, to be used by the music player and other pages.

// TODO: update old references to playlists, tracks, tracksLastModified
// TODO: how to properly to abstract class / interface in JS?
class Music {
    /**
     * @returns {Array<Playlist>}
     */
    async playlists() {
        throw new Error("not implemented");
    }

    /**
     * @param {string} name
     * @returns {Playlist|null}
     */
    async playlist(name) {
        throw new Error("not implemented");

    }

    /**
     * @returns {Array<Track>}
     */
    async tracks() {
        throw new Error("not implemented");
    }

    /**
     * @param {string} trackPath
     * @returns {Track|null}
     */
    async track(path) {
        throw new Error("not implemented");

    }
}

class OnDemandMusic extends Music {
    async playlists() {
        const response = await fetch('/playlists/list');
        const json = await response.json();
        const playlists = [];
        for (const playlistObj of json) {
            playlists.push(new Playlist(playlistObj));
        }
        return playlists;
    }

    async playlist(name) {
        const response = await fetch('/playlists/list');
        const json = await response.json();
        for (const playlistObj of json) {
            if (playlistObj.name == name) {
                return new Playlist(playlistObj);
            }
        }
        return null;
    }

    async tracks() {
        throw new Error("not supported")
    }

    async track(path) {
        const response = await fetch('/track/info?path=' + encodeURIComponent(path));
        const json = await response.json();
        return new Track(json.playlist, json);
    }
}

class LocalMusic extends Music {
    /** @type {Object.<string, Playlist>} */
    #playlists;
    /** @type {Object.<string, Track> | null} */
    #tracks;
    /** @type {number} */
    #tracksLastModified;

    async playlists() {
        return Object.values(this.#playlists);
    }

    async playlist(name) {
        return this.#playlists[name];
    }

    async tracks() {
        return Object.values(this.#tracks);
    }

    async track(path) {
        return this.#tracks[path];
    }

    async updateTrackList(trackFilter = null) {
        console.info('api: update track list');
        const response = await fetch('/track/list');
        const lastModified = response.headers.get('Last-Modified')

        if (lastModified == this.tracksLastModified) {
            console.info('api: track list is unchanged');
            // No need to do potentially expensive transformation to Track objects
            return;
        }
        this.tracksLastModified = lastModified;

        const json = await response.json();

        this.#playlists = {};
        this.#tracks = {};
        for (const playlistObj of json.playlists) {
            this.#playlists[playlistObj.name] = new Playlist(playlistObj);;
            for (const trackObj of playlistObj.tracks) {
                if (!trackFilter || trackFilter(trackObj)) {
                    this.#tracks[trackObj.path] = new Track(playlistObj.name, trackObj);
                }
            }
        }
    };
}

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

    async chooseRandomTrack(tagFilter) {
        const chooseResponse = await jsonPost('/track/choose', {'playlist_dir': this.name, ...tagFilter});
        const trackData = await chooseResponse.json();
        console.info('api: chosen track: ', trackData.path);
        return new Track(this.name, trackData);
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
     * @param {string} audioType
     * @param {boolean} stream
     * @param {boolean} memeCover
     * @returns {Promise<DownloadedTrack>}
     */
    async download(audioType, stream, memeCover) {
        const imageQuality = audioType == 'webm_opus_low' ? 'low' : 'high';
        const encodedPath = encodeURIComponent(this.path);

        const promises = [];

        const audioUrl = `/track/audio?path=${encodedPath}&type=${audioType}`;
        if (!stream) {
            promises.push(async function() {
                const trackResponse = await fetch(audioUrl);
                checkResponseCode(trackResponse);
                const audioBlob = await trackResponse.blob();
                console.debug('track: downloaded audio', audioUrl);
                return URL.createObjectURL(audioBlob);
            }());
        }

        const imageUrl = `/track/album_cover?path=${encodedPath}&quality=${imageQuality}&meme=${memeCover ? 1 : 0}`;
        if (!stream) {
            promises.push(async function() {
                const coverResponse = await fetch(imageUrl);
                checkResponseCode(coverResponse);
                const imageBlob = await coverResponse.blob();
                console.debug('track: downloaded image', imageUrl);
                return URL.createObjectURL(imageBlob);
            }());
        }

        promises.push(async function() {
            const lyricsUrl = `/track/lyrics?path=${encodedPath}`;
            const lyricsResponse = await fetch(lyricsUrl);
            checkResponseCode(lyricsResponse);
            const lyricsJson = await lyricsResponse.json();
            console.debug('track: downloaded lyrics', lyricsUrl);
            return lyricsJson.found ? new Lyrics(lyricsJson.source, lyricsJson.html) : null;
        }());

        // Download in parallel
        if (stream) {
            return new DownloadedTrack(this, audioUrl, imageUrl, await promises[0]);
        } else {
            return new DownloadedTrack(this, ...(await Promise.all(promises)));
        }
    }

    async delete() {
        const oldName = this.path.split('/').pop();
        const newName = '.trash.' + oldName;
        await jsonPost('/files/rename', {path: this.path, new_name: newName});
    }

    async dislike() {
        jsonPost('/dislikes/add', {track: this.path});
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
     * @type {lyrics}
     */
    lyrics;

    constructor(track, audioUrl, imageUrl, lyrics) {
        this.track = track;
        this.audioUrl = audioUrl;
        this.imageUrl = imageUrl;
        this.lyrics = lyrics;
    }

    revokeObjects() {
        console.debug('queue: revoke objects:', this.track.path);
        URL.revokeObjectURL(this.audioUrl);
        URL.revokeObjectURL(this.imageUrl);
    }
}

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
