// Replace timestamp by formatted time string
document.addEventListener('DOMContentLoaded', () => {
    for (const elem of document.getElementsByClassName('timestamp')) {
        const timestamp = elem.textContent;
        if (timestamp == 0) {
            elem.textContent = '-';
        } else {
            elem.textContent = new Date(1000 * elem.textContent).toLocaleString();
        }
    }
});
