const music = new Music();

document.addEventListener('DOMContentLoaded', () => {
    // TODO remove this event
    eventBus.publish(MusicEvent.TRACK_LIST_CHANGE);
});
