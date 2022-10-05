const visualise = {
    bars: 2048,
    analyser: null,
    dataArray: null,
    start: () => {
        // https://blog.logrocket.com/audio-visualizer-from-scratch-javascript/
        const audioContext = new AudioContext();
        const audioSource = audioContext.createMediaElementSource(getAudioElement());
        const analyser = audioContext.createAnalyser();
        audioSource.connect(analyser);
        audioSource.connect(audioContext.destination);
        visualise.analyser = analyser;
        visualise.dataArray = new Uint8Array(analyser.frequencyBinCount);
        visualise.repeat();
    },
    repeat: () => {
        visualise.analyser.fftSize = visualise.bars;
        const canvas = document.getElementById('visualiser');
        canvas.style.zIndex = 2;
        canvas.height = canvas.clientHeight;
        canvas.width = canvas.clientWidth;
        const draw = canvas.getContext('2d');
        const bufferLength = visualise.analyser.frequencyBinCount;
        // const upperSkip = Math.round(0.35*bufferLength);
        const skip = Math.round(0.15*bufferLength);
        const barWidth = canvas.width / (bufferLength - 2.0*skip);

        let x = 0;
        draw.clearRect(0, 0, canvas.height, canvas.width);
        visualise.analyser.getByteFrequencyData(visualise.dataArray);
        let finalI = 0;
        for (let i = skip; i < (bufferLength - skip); i++) {
            const barHeight = visualise.dataArray[i];
            draw.fillStyle = "white";
            draw.fillRect(x, canvas.height - barHeight, barWidth + 1, barHeight);
            x += barWidth;
            finalI = i;
        }

        console.info(canvas.width, bufferLength, skip, barWidth, finalI);

        requestAnimationFrame(visualise.repeat);
    }
};
