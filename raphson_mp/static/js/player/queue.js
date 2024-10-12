class Queue {
    /** @type {number} */
    maxHistorySize = 3;
    /** @type {string} */
    previousPlaylist;
    /** @type {Array<string>} */
    playlistOverrides = [];
    /** @type {boolean} */
    #fillBusy;
    /** @type {DownloadedTrack | null} */
    currentTrack;
    /** @type {Array<DownloadedTrack>} */
    previousTracks;
    /** @type {Array<DownloadedTrack>} */
    manualQueuedTracks;
    /** @type {Array<DownloadedTrack>} */
    autoQueuedTracks;

    constructor() {
        this.#fillBusy = false;
        this.currentTrack = null;
        this.previousTracks = [];
        this.manualQueuedTracks = []
        this.autoQueuedTracks = [];

        eventBus.subscribe(MusicEvent.METADATA_CHANGE, updatedTrack => {
            let queueChanged = false;
            for (const queue of [this.previousTracks, this.manualQueuedTracks, this.autoQueuedTracks]) {
                for (const downloadedTrack of queue) {
                    if (downloadedTrack.track && downloadedTrack.track.path == updatedTrack.path) {
                        console.debug('queue: updating track in queue following a METADATA_CHANGE event', updatedTrack.path);
                        downloadedTrack.track = updatedTrack;
                        queueChanged = true;
                    }
                }
            }
            if (queueChanged) {
                this.updateHtml();
            }
        });

        document.getElementById('queue-clear').addEventListener('click', () => {
            this.#combinedQueue().forEach(track => track.revokeObjects());
            this.manualQueuedTracks = [];
            this.autoQueuedTracks = [];
            this.fill();
        });

        document.addEventListener('DOMContentLoaded', () => this.fill());
    };

    /**
     * @returns {Array<DownloadedTrack}
     */
    #combinedQueue() {
        return [...this.manualQueuedTracks, ...this.autoQueuedTracks];
    }

    /**
     * @returns {Number}
     */
    #combinedQueueLength() {
        return this.manualQueuedTracks.length + this.autoQueuedTracks.length;
    }

    /**
     * @param {Number} start
     * @param {Number} deleteCount
     * @param  {...DownloadedTrack} insertTracks
     * @returns {Array<DownloadedTrack>}
     */
    #combinedQueueSplice(start, deleteCount, ...insertTracks) {
        if (start < this.manualQueuedTracks.length) {
            return this.manualQueuedTracks.splice(start, deleteCount, ...insertTracks);
        } else {
            return this.autoQueuedTracks.splice(start - this.manualQueuedTracks.length, deleteCount, ...insertTracks);
        }
    }

    /**
     * @returns {DownloadedTrack | null}
     */
    getPreviousTrack() {
        if (this.previousTracks.length > 0) {
            return this.previousTracks[this.previousTracks.length - 1];
        } else {
            return null;
        }
    };

    fill() {
        this.updateHtml(); // TODO only update HTML if queue has actually changed

        if (this.#fillBusy) {
            return;
        }

        let minQueueSize = parseInt(document.getElementById('settings-queue-size').value);

        if (!isFinite(minQueueSize)) {
            minQueueSize = 1;
        }

        if (this.autoQueuedTracks.length >= minQueueSize) {
            return;
        }

        let playlist;

        if (this.playlistOverrides.length > 0) {
            playlist = this.playlistOverrides.pop();
            console.debug('queue: override', playlist);
        } else {
            playlist = getNextPlaylist(this.previousPlaylist);
            console.debug(`queue: round robin: ${this.previousPlaylist} -> ${playlist}`);
            this.previousPlaylist = playlist;
        }

        if (playlist === null) {
            console.debug('queue: no playlists selected, trying again later');
            document.getElementById('no-playlists-selected').classList.remove('hidden');
            setTimeout(() => this.fill(), 1000);
            return;
        }
        document.getElementById('no-playlists-selected').classList.add('hidden');

        this.#fillBusy = true;

        queue.addRandomTrackFromPlaylist(playlist).then(() => {
            this.#fillBusy = false;
            this.fill();
        }, error => {
            console.warn('queue: error');
            console.warn(error);
            this.#fillBusy = false;
            setTimeout(() => this.fill(), 5000);
        });
    };

    /**
     * @param {string} playlistName Playlist directory name
     */
    async addRandomTrackFromPlaylist(playlistName) {
        const playlist = await music.playlist(playlistName);
        const track = await playlist.chooseRandomTrack(false, getTagFilter());
        const downloadedTrack = await track.download(...getTrackDownloadParams());
        this.add(downloadedTrack, false);
    };

    updateHtml() {
        document.getElementsByTagName("body")[0].style.cursor = this.#fillBusy ? 'progress' : '';

        const rows = [];
        let i = 0;
        let totalQueueDuration = 0;
        for (const queuedTrack of this.#combinedQueue()) {
            const track = queuedTrack.track;

            if (track != null) {
                totalQueueDuration += track.duration;
            }

            // Trash can that appears when hovering - click to remove track
            const tdCover = document.getElementById('template-td-cover').content.cloneNode(true).firstElementChild;
            tdCover.style.backgroundImage = `url("${queuedTrack.imageUrl}")`;
            const rememberI = i;
            tdCover.onclick = () => queue.removeFromQueue(rememberI);

            // Track title HTML
            const tdTrack = document.createElement('td');
            tdTrack.appendChild(track != null ? track.displayHtml(true) : trackInfoUnavailableSpan());

            // Add columns to <tr> row and add the row to the table
            const row = document.createElement('tr');
            row.dataset.queuePos = i;
            row.appendChild(tdCover);
            row.appendChild(tdTrack);

            rows.push(row);
            i++;
        }

        document.getElementById('current-queue-size').textContent =
                this.#combinedQueueLength() + ' / ' + durationToString(totalQueueDuration);

        // If the queue is still loading (size smaller than target size), add a loading spinner
        const minQueueSize = parseInt(document.getElementById('settings-queue-size').value);
        if (i < minQueueSize) {
            rows.push(document.getElementById('template-queue-spinner').content.cloneNode(true));
        }

        // Add events to <tr> elements
        queue.#dragDropTable(rows);

        const outerDiv = document.getElementById('queue-table');
        outerDiv.replaceChildren(...rows);
    };

    removeFromQueue(index) {
        const track = this.#combinedQueueSplice(index, 1)[0];
        track.revokeObjects();
        const removalBehaviour = document.getElementById('settings-queue-removal-behaviour').value;
        if (removalBehaviour === 'same') {
            // Add playlist to override array. Next time a track is picked, when playlistOverrides contains elements,
            // one element is popped and used instead of choosing a random playlist.
            this.playlistOverrides.push(track.playlistName);
        } else if (removalBehaviour !== 'roundrobin') {
            console.warn('queue: unexpected removal behaviour: ' + removalBehaviour);
        }
        this.fill();
    };

    // Based on https://code-boxx.com/drag-drop-sortable-list-javascript/
    /**
     * @param {Array<HTMLTableRowElement>} rows
     */
    #dragDropTable(rows) {
        let current = null; // Element that is being dragged

        for (let row of rows) {
            row.draggable = true; // Make draggable

            // The .hint class is purely cosmetic, it may be styled using css
            // Currently disabled because no CSS is applied

            row.ondragstart = () => {
                current = row;
                // for (let row2 of rows) {
                //     if (row2 != current) {
                //         row2.classList.add('hint');
                //     }
                // }
            };

            // row.ondragend = () => {
            //     for (let row2 of rows) {
            //         row2.classList.remove("hint");
            //     }
            // };

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
                const track = this.#combinedQueueSplice(currentPos, 1)[0];
                // Add it to the place it was dropped
                this.#combinedQueueSplice(targetPos, 0, track);
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
        this.manualQueuedTracks.unshift(this.currentTrack);
        // Replace current track with last track in history
        this.currentTrack = this.previousTracks.pop();

        eventBus.publish(MusicEvent.TRACK_CHANGE);
        this.updateHtml();
    };

    next() {
        if (this.#combinedQueueLength() === 0) {
            console.debug('queue: is empty, try to play next track again later');
            setTimeout(() => this.next(), 1000);
            return;
        }

        // Add current track to history
        if (this.currentTrack !== null) {
            this.previousTracks.push(this.currentTrack);
            // If history exceeded maximum length, remove first (oldest) element
            if (this.previousTracks.length > this.maxHistorySize) {
                const removedTrack = this.previousTracks.shift();
                removedTrack.revokeObjects();
            }
        }

        // Replace current track with first item from queue
        if (this.manualQueuedTracks.length) {
            this.currentTrack = this.manualQueuedTracks.shift();
        } else {
            this.currentTrack = this.autoQueuedTracks.shift();
        }

        eventBus.publish(MusicEvent.TRACK_CHANGE);
        this.fill();
    };

    /**
     * Add track to queue
     * @param {DownloadedTrack} downloadedTrack
     * @param {boolean} manual True to add track to the manual queue instead of auto queue (manual queue is played first)
     * @param {boolean} top True to add track to top of queue
     */
    add(downloadedTrack, manual, top = false) {
        const queue = (manual ? this.manualQueuedTracks : this.autoQueuedTracks)
        if (top) {
            queue.unshift(downloadedTrack);
        } else {
            queue.push(downloadedTrack);
        }
        this.updateHtml();
    };
};

const queue = new Queue();
