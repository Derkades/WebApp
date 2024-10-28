// Browser "restore session" functionality can sometimes restore a very outdated version of the page
// In that case, trigger a reload
// This does have the side effect that any device with a significantly wrong clock cannot use the music player.

document.addEventListener('DOMContentLoaded', () => {
    const loadTimestamp = parseInt(document.getElementById('load-timestamp').textContent);
    const differenceSeconds = Date.now() / 1000 - loadTimestamp;

    console.debug('reload: page loaded ' + differenceSeconds + ' ago');

    if (differenceSeconds > 86400) {
        console.warn('page loaded long ago, reloading page!')
        window.location.reload();
    }
});
