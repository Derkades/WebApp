// File name starts with 1 so it is included at the start of the concatenated player.js script, after 0strict

const MusicEvent = {
    METADATA_CHANGE: 'metadata_change', // Tracks or playlists have been changed, added, or removed. Any HTML with playlist/track info should be updated. Track with updated metadata may be provided as parameter to the callable.
    TRACK_CHANGE: 'track_change', // Track that is playing changed (skipped to next or previous track)
    SETTINGS_LOADED: 'settings_loaded',
}

class EventBus {
    /** @type{Object.<string, Array<Function>} */
    listeners;

    constructor() {
        this.listeners = {};

        for (const event of Object.values(MusicEvent)) {
            this.listeners[event] = [];
        }
    }

    subscribe(name, callable) {
        this.listeners[name].push(callable);
    }

    publish(name, ...params) {
        for (const callable of this.listeners[name]) {
            try {
                callable(...params);
            } catch (error) {
                console.error('error in event listener', error);
            }
        }
    }

}

const eventBus = new EventBus();
