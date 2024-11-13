class Windows {
    baseIndex;
    #openWindows;

    constructor() {
        this.baseIndex = 100;
        this.#openWindows = [];
    }

    /**
     * Open a window, above other windows. If the window is already opens, it is just moved to the top.
     * @param {string} idToOpen HTML id of window element
     */
    open(idToOpen) {
        console.debug('window: open:', idToOpen);

        const windowToOpen = document.getElementById(idToOpen);
        if (!windowToOpen.classList.contains('window-overlay')) {
            throw new Error('Window is missing window-overlay class');
        }

        if (this.#openWindows.indexOf(idToOpen) !== -1) {
            // Already open, elevate existing window to top

            // Create new array with window to open removed, then add it on top
            this.#openWindows = this.#openWindows.filter(openWindow => openWindow !== windowToOpen);
            this.#openWindows.push(idToOpen);

            // Change z-index of all open windows
            let i = 1;
            for (const openWindow of this.#openWindows) {
                console.debug('window: is open:', openWindow);
                document.getElementById(openWindow).style.zIndex = this.baseIndex + i++;
            }
        } else {
            // Add window to top (end of array), set z-index and make visible
            this.#openWindows.push(idToOpen);
            windowToOpen.style.zIndex = this.baseIndex + this.#openWindows.indexOf(idToOpen);
            windowToOpen.classList.remove('overlay-hidden');
        }
    }

    /**
     * Close a specific window
     * @param {string} idToClose HTML id of window element
     */
    close(idToClose) {
        console.debug('window: close:', idToClose);

        // Hide closed window
        document.getElementById(idToClose).classList.add('overlay-hidden');

        // Remove closed window from array
        this.#openWindows = this.#openWindows.filter(id => id !== idToClose);

        // Update z-index for open windows
        let zIndex = 0;
        for (const id of this.#openWindows) {
            document.getElementById(id).style.zIndex = this.baseIndex + zIndex++;
        }
    }

    /**
     * Close top window
     */
    closeTop() {
        if (this.#openWindows.length > 0) {
            this.close(this.#openWindows.pop());
        }
    }

    isOpen(id) {
        return !document.getElementById(id).classList.contains('overlay-hidden');
    }

}

const windows = new Windows();

document.addEventListener('DOMContentLoaded', () => {
    // Window open buttons
    for (const elem of document.getElementsByClassName('window-overlay')) {
        const openButton = document.getElementById('open-' + elem.id);
        if (openButton === null) {
            continue;
        }
        const id = elem.id;
        openButton.addEventListener('click', () => windows.open(id));
    }

    // Window close buttons
    for (const elem of document.getElementsByClassName('window-close-button')) {
        const id = elem.dataset.for;
        if (id === undefined) {
            console.warn('Window close button has no data-for attribute');
            continue;
        }
        elem.addEventListener('click', () => windows.close(id));
    }
});
