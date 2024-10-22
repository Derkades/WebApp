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

    /**
     * Called every minute. Checks if news should be queued.
     * @returns {void}
     */
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

    /**
     * Downloads news, and add it to the queue
     */
    async queue() {
        const track = await music.downloadNews();
        queue.add(queuedTrack, true, true)
    }
}

const news = new News();
