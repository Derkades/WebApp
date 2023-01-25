// Replace timestamp by formatted time string
document.addEventListener('DOMContentLoaded', () => {
    for (const elem of document.getElementsByClassName('format-timestamp')) {
        const timestamp = elem.textContent;
        if (timestamp == 0) {
            elem.textContent = '-';
        } else {
            elem.textContent = new Date(1000 * elem.textContent).toLocaleString();
        }
    }

    for (const elem of document.getElementsByClassName('format-duration')) {
        const hhmmss =  new Date(1000 * elem.textContent).toISOString().substring(11, 19);
        if (hhmmss.startsWith('00:')) {
            elem.textContent = hhmmss.substring(3);
        } else {
            elem.textContent = hhmmss;
        }
    }
});
