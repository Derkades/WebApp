class Queue {
    /** @type {boolean} */
    #fillBusy;
    /** @type {QueuedTrack | null} */
    currentTrack;
    /** @type {Array<QueuedTrack>} */
    previousTracks;
    /** @type {Array<QueuedTrack>} */
    queuedTracks;

    constructor() {
        this.#fillBusy = false;
        this.currentTrack = null;
        this.previousTracks = [];
        this.queuedTracks = [];

        eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, () => {
            this.updateHtml();
        });
    };

    /**
     * @returns {QueuedTrack | null}
     */
    getPreviousTrack() {
        if (this.previousTracks.length > 0) {
            return this.previousTracks[this.previousTracks.length - 1];
        } else {
            return null;
        }
    };

    fill() {
        this.updateHtml();

        if (this.#fillBusy) {
            return;
        }

        let minQueueSize = parseInt(document.getElementById('settings-queue-size').value);

        if (!isFinite(minQueueSize)) {
            minQueueSize = 1;
        }

        if (this.queuedTracks.length >= minQueueSize) {
            return;
        }

        let playlist;

        if (state.playlistOverrides.length > 0) {
            playlist = state.playlistOverrides.pop();
            console.debug('queue override', playlist);
        } else {
            playlist = getNextPlaylist(state.lastChosenPlaylist);
            console.debug(`queue round robin: ${state.lastChosenPlaylist} -> ${playlist}`);
            state.lastChosenPlaylist = playlist;
        }

        if (playlist === null) {
            console.debug('queue no playlists selected, trying again later');
            document.getElementById('no-playlists-selected').classList.remove('hidden');
            setTimeout(() => this.fill(), 500);
            return;
        }
        document.getElementById('no-playlists-selected').classList.add('hidden');

        this.#fillBusy = true;

        Queue.downloadRandomAndAddToQueue(playlist).then(() => {
            this.#fillBusy = false;
            this.fill();
        }, error => {
            console.warn('queue | error');
            console.warn(error);
            this.#fillBusy = false;
            setTimeout(() => this.fill(), 5000);
        });
    };

    /**
     * @param {string} playlist Playlist directory name
     */
    static async downloadRandomAndAddToQueue(playlist) {
        console.debug('Choose track');
        const chooseResponse = await jsonPost('/track/choose', {'playlist_dir': playlist, ...getTagFilter()});
        const path = (await chooseResponse.json()).path;

        console.info('Chosen track', path);

        // Find track info for this file
        const track = state.tracks[path];

        if (track === undefined) {
            throw Error('Track does not exist in local list: ' + path);
        }

        await track.downloadAndAddToQueue();
    };

    updateHtml() {
        document.getElementsByTagName("body")[0].style.cursor = this.#fillBusy ? 'progress' : '';

        const rows = [];
        let i = 0;
        let totalQueueDuration = 0;
        for (const queuedTrack of this.queuedTracks) {
            const track = queuedTrack.track();

            if (track !== null) {
                totalQueueDuration += track.duration;
            }

            // Trash can that appears when hovering - click to remove track
            const tdCover = document.getElementById('template-td-cover').content.cloneNode(true).firstElementChild;
            tdCover.style.backgroundImage = `url("${queuedTrack.imageBlobUrl}")`;
            const rememberI = i;
            tdCover.onclick = () => queue.removeFromQueue(rememberI);

            // Track title HTML
            const tdTrack = document.createElement('td');
            if (track !== null) {
                tdTrack.appendChild(track.displayHtml(true));
            } else {
                tdTrack.textContent = '[track info unavailable]';
            }

            // Add columns to <tr> row and add the row to the table
            const row = document.createElement('tr');
            row.dataset.queuePos = i;
            row.appendChild(tdCover);
            row.appendChild(tdTrack);

            rows.push(row);
            i++;
        }

        document.getElementById('current-queue-size').textContent = this.queuedTracks.length + ' - ' + durationToString(totalQueueDuration);

        // If the queue is still loading (size smaller than target size), add a loading spinner
        const minQueueSize = parseInt(document.getElementById('settings-queue-size').value);
        if (i < minQueueSize) {
            rows.push(document.getElementById('template-queue-spinner').content.cloneNode(true));
        }

        const outerDiv = document.getElementById('queue-table');
        outerDiv.replaceChildren(...rows);
        // Add events to <tr> elements
        queue.dragDropTable();
    };

    removeFromQueue(index) {
        const track = this.queuedTracks.splice(index, 1)[0];
        track.revokeObjects();
        const removalBehaviour = document.getElementById('settings-queue-removal-behaviour').value;
        if (removalBehaviour === 'same') {
            // Add playlist to override array. Next time a track is picked, when playlistOverrides contains elements,
            // one element is popped and used instead of choosing a random playlist.
            state.playlistOverrides.push(track.playlistName);
        } else if (removalBehaviour !== 'roundrobin') {
            console.warn('unexpected removal behaviour: ' + removalBehaviour);
        }
        this.fill();
    };

    // Based on https://code-boxx.com/drag-drop-sortable-list-javascript/
    dragDropTable() {
        let items = document.getElementById('queue-table').getElementsByTagName("tr");
        let current = null; // Element that is being dragged

        for (let row of items) {
            row.draggable = true; // Make draggable

            // The .hint class is purely cosmetic, it may be styled using css

            row.ondragstart = () => {
                current = row;
                for (let it of items) {
                    if (it != current) {
                        it.classList.add('hint');
                    }
                }
            };

            row.ondragend = () => {
                for (let it of items) {
                    it.classList.remove("hint");
                }
            };

            row.ondragover = event => event.preventDefault();

            row.ondrop = (event) => {
                event.preventDefault();

                if (row == current) {
                    // No need to do anything if row was put back in same location
                    return;
                }

                const currentPos = current.dataset.queuePos;
                const targetPos = row.dataset.queuePos;
                // Remove current (being dragged) track from queue
                const track = this.queuedTracks.splice(currentPos, 1)[0];
                // Add it to the place it was dropped
                this.queuedTracks.splice(targetPos, 0, track);
                // Now re-render the table
                this.updateHtml();
            };
        };
    };

    previous() {
        if (this.previousTracks.length == 0) {
            return;
        }

        // Move current track to beginning of queue
        this.queuedTracks.unshift(this.currentTrack);
        // Replace current track with last track in history
        this.currentTrack = this.previousTracks.pop();

        eventBus.publish(MusicEvent.TRACK_CHANGE);
        this.updateHtml();
    };

    next() {
        if (this.queuedTracks.length === 0) {
            console.log('Queue is empty, try to play next track again later');
            setTimeout(() => this.next(), 1000);
            return;
        }

        // Add current track to history
        if (this.currentTrack !== null) {
            this.previousTracks.push(this.currentTrack);
            // If history exceeded maximum length, remove first (oldest) element
            if (this.previousTracks.length > state.maxHistorySize) {
                const removedTrack = this.previousTracks.shift();
                removedTrack.revokeObjects();
            }
        }

        // Replace current track with first item from queue
        this.currentTrack = this.queuedTracks.shift();

        eventBus.publish(MusicEvent.TRACK_CHANGE);
        this.fill();
    };

    /**
     * Add track to queue
     * @param {QueuedTrack} queuedTrack
     * @param {boolean} top True to add track to the top of the queue, false to add to the bottom
     */
    add(queuedTrack, top) {
        if (top) {
            this.queuedTracks.unshift(queuedTrack);
        } else {
            this.queuedTracks.push(queuedTrack);
        }
        this.updateHtml();
    };
};

class QueuedTrack {
    /** @type {string} */
    trackPath;
    /** @type {string} */
    audioBlobUrl;
    /** @type {string} */
    imageBlobUrl;
    /** @type {string} */
    lyrics;

    /**
     * @param {Track} track
     * @param {string} audioBlobUrl
     * @param {string} imageBlobUrl
     * @param {string} lyrics
     */
    constructor(track, audioBlobUrl, imageBlobUrl, lyrics) {
        this.trackPath = track.path;
        this.audioBlobUrl = audioBlobUrl;
        this.imageBlobUrl = imageBlobUrl;
        this.lyrics = lyrics;
    };

    /**
     * @returns {Track | null} Track info, or null if the track has since been deleted
     */
    track() {
        if (this.trackPath in state.tracks) {
            return state.tracks[this.trackPath];
        } else {
            return null;
        }
    }

    revokeObjects() {
        console.debug('Revoke objects', this.trackPath);
        URL.revokeObjectURL(this.audioBlobUrl);
        URL.revokeObjectURL(this.imageBlobUrl);
    }
};

const queue = new Queue();
