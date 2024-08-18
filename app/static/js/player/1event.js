const MusicEvent = {
    METADATA_CHANGE: 'metadata_change', // Tracks or playlists have been changed, added, or removed. Any HTML with playlist/track info should be updated.
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

    publish(name) {
        for (const callable of this.listeners[name]) {
            try {
                callable();
            } catch (error) {
                console.error('error in event listener', error);
            }
        }
    }

}

const eventBus = new EventBus();
