class News {
    /** @type {HTMLOptionElement} */
    #newsSetting;
    /** @type {boolean} */
    #hasQueuedNews;

    constructor() {
        document.addEventListener('DOMContentLoaded', () => {
            this.#newsSetting = document.getElementById('settings-news');
            setInterval(() => this.check(), 60_000);
        });
    }

    check() {
        if (!this.#newsSetting.checked) {
            console.debug('news: is disabled')
            return;
        }

        const minutes = new Date().getMinutes();
        const isNewsTime = minutes >= 6 && minutes < 8;
        if (!isNewsTime) {
            console.debug('news: not news time');
            this.#hasQueuedNews = false;
            return;
        }

        if (this.#hasQueuedNews) {
            console.debug('news: already queued');
            return;
        }

        if (getAudioElement().paused) {
            console.debug('news: will not queue, audio paused');
            return;
        }

        console.debug('news: queueing news');
        this.queue().then(() => this.#hasQueuedNews = true);
    }

    async queue() {
        const audioResponse = await fetch('/news/audio');
        checkResponseCode(audioResponse);
        const audioBlob = URL.createObjectURL(await audioResponse.blob());

        const imageResponse = await fetch('/static/img/raphson.png');
        checkResponseCode(imageResponse);
        const imageBlob = URL.createObjectURL(await imageResponse.blob());

        const queuedTrack = new DownloadedTrack(null, audioBlob, imageBlob, null);
        queue.add(queuedTrack, true, true)
    }
}

const news = new News();
