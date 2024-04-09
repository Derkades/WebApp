class Music {
    /** @type {Object.<string, Playlist>} */
    playlists;
    /** @type {Object.<string, Track> | null} */
    tracks;
    /** @type {number} */
    tracksLastModified;

    constructor() {
        document.addEventListener('DOMContentLoaded', () => {
            this.initTrackList();
            setInterval(() => this.updateTrackList(), 2*60*1000);
        });
    }

    initTrackList() {
        this.updateTrackList()
            .then(() => {
                // Hide loading overlay when track list has finished loading
                document.getElementById('loading-overlay').classList.add('overlay-hidden')
            })
            .catch(err => {
                console.warn('music: error retrieving initial track list', err);
                setTimeout(() => this.initTrackList(), 1000);
            });
    }

    async updateTrackList() {
        console.info('music: update track list');
        const response = await fetch('/track/list');
        const lastModified = response.headers.get('Last-Modified')

        if (lastModified == this.tracksLastModified) {
            console.info('music: track list is unchanged');
            return;
        }
        this.tracksLastModified = lastModified;

        const json = await response.json();

        this.playlists = {};
        this.tracks = {};
        for (const playlistObj of json.playlists) {
            this.playlists[playlistObj.name] = new Playlist(playlistObj);;
            for (const trackObj of playlistObj.tracks) {
                this.tracks[trackObj.path] = new Track(playlistObj.name, trackObj);
            }
        }

        eventBus.publish(MusicEvent.TRACK_LIST_CHANGE);
    };
}

const music = new Music();
