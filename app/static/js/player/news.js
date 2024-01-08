class News {
    /** @type {HTMLOptionElement} */
    #newsSetting;
    /** @type {boolean} */
    #hasQueuedNews;

    constructor() {
        document.addEventListener('DOMContentLoaded', () => {
            this.#newsSetting = document.getElementById('settings-news');
            setInterval(() => this.check(), 60000);
        });
    }

    check() {
        const provider = this.#newsSetting.value;
        if (provider == 'disabled') {
            console.debug('news: is disabled')
            return;
        }

        const minutes = new Date().getMinutes();
        const isNewsTime = minutes < 7 || minutes > 57;
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

        console.debug('news: queueing news from provider: ', provider);
        this.queue(provider).then(() => this.#hasQueuedNews = true);
    }

    async queue(provider) {
        const audioResponse = await fetch('/news/audio?provider=' + encodeURIComponent(provider));
        checkResponseCode(audioResponse);
        const audioBlob = URL.createObjectURL(await audioResponse.blob());

        const imageResponse = await fetch('/static/img/raphson.png');
        checkResponseCode(imageResponse);
        const imageBlob = URL.createObjectURL(await imageResponse.blob());

        const queuedTrack = new QueuedTrack(null, audioBlob, imageBlob, "News");
        queue.add(queuedTrack, true)
    }
}

const news = new News();
