const MusicEvent = {
    TRACK_LIST_CHANGE: 'track_list_change', // Local playlist and track list state has been updated. All dependent HTML should be updated.
    TRACK_CHANGE: 'track_change', // Track that is playing changed (skipped to next or previous track)
    PLAYBACK_CHANGE: 'playback_change', // Music played, paused, or change in current position in track
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

eventBus.subscribe(MusicEvent.TRACK_CHANGE, () => eventBus.publish(MusicEvent.PLAYBACK_CHANGE));

document.addEventListener('DOMContentLoaded', () => {
    setInterval(() => eventBus.publish(MusicEvent.PLAYBACK_CHANGE), 1000);
});
