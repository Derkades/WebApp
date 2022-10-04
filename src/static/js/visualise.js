const visualise = {
    bars: 1024,
    analyser: null,
    dataArray: null,
    start: () => {
        // https://blog.logrocket.com/audio-visualizer-from-scratch-javascript/
        const audioContext = new AudioContext();
        const audioSource = audioContext.createMediaElementSource(getAudioElement());
        const analyser = audioContext.createAnalyser();
        audioSource.connect(analyser);
        audioSource.connect(audioContext.destination);
        analyser.fftSize = visualise.bars;
        visualise.analyser = analyser;
        visualise.dataArray = new Uint8Array(analyser.frequencyBinCount);
        visualise.repeat();
    },
    repeat: () => {
        const height = window.innerHeight / 4;
        const width = window.innerWidth;
        const canvas = document.getElementById('visualiser');
        canvas.style.zIndex = 2;
        canvas.height = height;
        canvas.width = width;
        const draw = canvas.getContext('2d');
        const bufferLength = visualise.analyser.frequencyBinCount;
        const upperSkip = Math.round(0.35*bufferLength);
        const barWidth = width / (bufferLength - upperSkip);
        let x = 0;
        draw.clearRect(0, 0, height, width);
        visualise.analyser.getByteFrequencyData(visualise.dataArray);
        for (let i = 0; i < (bufferLength - upperSkip); i++) {
            const barHeight = visualise.dataArray[i];
            draw.fillStyle = "white";
            draw.fillRect(x, height - barHeight, barWidth, barHeight);
            x += barWidth;
        }

        requestAnimationFrame(visualise.repeat);
    }
};
