// https://blog.logrocket.com/audio-visualizer-from-scratch-javascript/
class Visualiser {
    // Settings
    fftSize = 2**14;
    bassFreq = 50;
    minFreq = 50;
    maxFreq = 14000;
    xToFreqExp = 2;
    bassScaleAmount = 0.1;
    bassScaleEnabled = false;

    /** @type {AnalyserNode} */
    #analyser;
    /** @type {Uint8Array} */
    #dataArray;
    /** @type {HTMLCanvasElement} */
    #canvas;
    /** @type {boolean} */
    #needRedraw;

    start() {
        this.#canvas = document.getElementById('visualiser');

        const audioContext = new AudioContext();
        const audioSource = audioContext.createMediaElementSource(getAudioElement());
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = this.fftSize;
        audioSource.connect(analyser);
        audioSource.connect(audioContext.destination);
        this.#analyser = analyser;
        this.#dataArray = new Uint8Array(analyser.frequencyBinCount);
        this.#draw();

        setInterval(() => this.#update(), 1000/45);
        setInterval(() => this.#resize(), 1000);
    }

    #update() {
        this.#analyser.getByteFrequencyData(this.#dataArray);
        this.#needRedraw = true;
    }

    #resize() {

    }

    #draw() {
        if (this.#needRedraw) {
            this.#needRedraw = false;

            this.#canvas.height = this.#canvas.clientHeight;
            this.#canvas.width = this.#canvas.clientWidth;

            const height = this.#canvas.clientHeight;
            const width = this.#canvas.clientWidth;

            const draw = this.#canvas.getContext('2d');

            draw.clearRect(0, 0, height, width);
            draw.fillStyle = "white";

            const barWidth = 2;

            const minBin = this.minFreq / 48000 * this.fftSize;
            const maxBin = this.maxFreq / 48000 * this.fftSize;
            const multiplyX = (maxBin - minBin);

            for (let x = 0; x < width; x+= barWidth) {
                const i = Math.floor((x / width)**this.xToFreqExp * multiplyX + minBin);
                const barHeight = this.#dataArray[i];
                draw.fillRect(x, this.#canvas.height - barHeight, barWidth, barHeight);
            }

            if (this.bassScaleEnabled) {
                const bassIndex = Math.floor(this.bassFreq / 48000 * this.fftSize);
                const bassAmount = this.#dataArray[bassIndex] / 256;
                document.getElementsByTagName('body')[0].style.scale = 1 + bassAmount * this.bassScaleAmount;
            }
        }

        requestAnimationFrame(() => this.#draw());
    }

}

const visualiser = new Visualiser();

document.addEventListener('DOMContentLoaded', () => {
    // visualiser.start();
});
