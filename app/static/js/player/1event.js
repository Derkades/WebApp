const MusicEvent = {
    TRACK_LIST_CHANGE: 'track_list_change', // Local playlist and track list state has been updated. All dependent HTML should be updated.
    TRACK_CHANGE: 'track_change', // Track that is playing changed (skipped to next or previous track)
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
            callable();
        }
    }

}

const eventBus = new EventBus();
