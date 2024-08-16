const music = new Music();

document.addEventListener('DOMContentLoaded', () => {
    music.updateTrackList()
        .then(() => {
            // Hide loading overlay when track list has finished loading
            document.getElementById('loading-overlay').classList.add('overlay-hidden')
        })
        .catch(err => {
            console.warn('music: error retrieving initial track list', err);
            setTimeout(() => this.initTrackList(), 1000);
        });

    setInterval(async function() {
        await this.updateTrackList()
        eventBus.publish(MusicEvent.TRACK_LIST_CHANGE);
    }, 2*60*1000);
});
