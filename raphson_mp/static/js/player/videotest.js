document.addEventListener('DOMContentLoaded', () => {
    const videoBox = document.getElementById('video-box');

    const video = document.createElement('video');
    videoBox.replaceChildren(video);

    setInterval(() => {
        video.load();
    }, 2000);
});
