// https://blog.logrocket.com/audio-visualizer-from-scratch-javascript/
class Visualiser {
    #fftSize = 2**14;
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
        this.#canvas.style.zIndex = 2;

        const audioContext = new AudioContext();
        const audioSource = audioContext.createMediaElementSource(getAudioElement());
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = this.#fftSize;
        audioSource.connect(analyser);
        audioSource.connect(audioContext.destination);
        this.#analyser = analyser;
        this.#dataArray = new Uint8Array(analyser.frequencyBinCount);
        this.#draw();

        setInterval(() => this.#update(), 1000/60);
    }

    #update() {
        this.#canvas.height = this.#canvas.clientHeight;
        this.#canvas.width = this.#canvas.clientWidth;
        this.#analyser.getByteFrequencyData(this.#dataArray);
        this.#needRedraw = true;
    }

    #draw() {
        if (this.#needRedraw) {
            this.#needRedraw = false;

            const draw = this.#canvas.getContext('2d');

            draw.clearRect(0, 0, this.#canvas.height, this.#canvas.width);
            draw.fillStyle = "white";

            const barWidth = 2;

            const minFreq = 50;
            const maxFreq = 18000;
            const minBin = minFreq / 48000 * this.#fftSize; // 4
            const maxBin = maxFreq / 48000 * this.#fftSize; // 1365
            const multiplyX = (maxBin - minBin) + minBin;

            for (let x = 0; x < this.#canvas.width; x+= barWidth) {
                const i = Math.floor((x / this.#canvas.width)**1.7 * multiplyX);
                const barHeight = this.#dataArray[i];
                draw.fillRect(x, this.#canvas.height - barHeight, barWidth, barHeight);
            }
        }

        requestAnimationFrame(() => this.#draw());
    }

}

const visualiser = new Visualiser();
