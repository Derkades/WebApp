// https://blog.logrocket.com/audio-visualizer-from-scratch-javascript/
class Visualiser {
    // Settings
    #barWidth = 10;
    #minFreq = 50;
    #maxFreq = 14000;
    #xToFreqExp = 2;

    /** @type {Uint8Array} */
    #dataArray;
    /** @type {HTMLCanvasElement} */
    #canvas;
    /** @type {number} */
    #taskId = null;

    constructor() {
        this.#canvas = document.getElementById('visualiser');
        this.#dataArray = new Uint8Array(audioContextManager.fftSize);
    }

    stop() {
        console.info('visualiser: stopped');
        this.#canvas.style.transform = 'translateY(100%)';
        clearInterval(this.#taskId);
        if (this.#taskId != null) {
            cancelAnimationFrame(this.#taskId)
            this.#taskId = null;
        }
    }

    start() {
        // Prevent double animation in case start() is accidentally called twice
        if (this.#taskId != null) {
            console.warn('visualiser: was already running');
            cancelAnimationFrame(this.#taskId);
        }

        console.info('visualiser: started');
        this.#canvas.style.transform = null;
        this.#taskId = requestAnimationFrame(() => this.#draw());
    }

    #draw() {
        if (!audioContextManager.analyser) {
            return;
        }

        const height = this.#canvas.clientHeight;
        const width = this.#canvas.clientWidth;

        this.#canvas.height = height;
        this.#canvas.width = width;

        const draw = this.#canvas.getContext('2d');

        draw.clearRect(0, 0, height, width);
        draw.fillStyle = "white";

        audioContextManager.analyser.getByteFrequencyData(this.#dataArray);

        const minBin = this.#minFreq / 48000 * audioContextManager.fftSize;
        const maxBin = this.#maxFreq / 48000 * audioContextManager.fftSize;
        const multiplyX = (maxBin - minBin);

        for (let x = 0; x < width; x += this.#barWidth) {
            const i = Math.floor((x / width)**this.#xToFreqExp * multiplyX + minBin);
            const barHeight = this.#dataArray[i] * height / 256;
            draw.fillRect(x, height - barHeight, this.#barWidth, barHeight);
        }

        this.#taskId = requestAnimationFrame(() => this.#draw());
    }
}

const visualiser = new Visualiser();

eventBus.subscribe(MusicEvent.SETTINGS_LOADED, () => {
    const checkbox = document.getElementById('settings-visualiser');

    function updateVisualiserState() {
        if (checkbox.checked && !getAudioElement().paused && document.visibilityState == 'visible') {
            visualiser.start();
        } else {
            visualiser.stop();
        }
    }

    checkbox.addEventListener('change', updateVisualiserState);
    getAudioElement().addEventListener('play', updateVisualiserState);
    getAudioElement().addEventListener('pause', updateVisualiserState);
    document.addEventListener('visibilitychange', updateVisualiserState);
});
