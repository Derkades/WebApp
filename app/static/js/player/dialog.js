class Dialogs {
    baseIndex;
    #openDialogs;

    constructor() {
        this.baseIndex = 100;
        this.#openDialogs = [];
    }

    /**
     * Open a dialog, above other dialogs. If the dialog is already opens, it is just moved to the top.
     * @param {string} idToOpen HTML id of dialog element
     */
    open(idToOpen) {
        console.debug('dialog: open:', idToOpen);

        const dialogToOpen = document.getElementById(idToOpen);
        if (!dialogToOpen.classList.contains('dialog-overlay')) {
            throw new Error('Dialog is missing dialog-overlay class');
        }

        if (this.#openDialogs.indexOf(idToOpen) !== -1) {
            // Already open, elevate existing dialog to top

            // Create new array with dialog to open removed, then add it on top
            this.#openDialogs = this.#openDialogs.filter(openDialog => openDialog !== dialogToOpen);
            this.#openDialogs.push(idToOpen);

            // Change z-index of all open dialogs
            let i = 1;
            for (const openDialog of this.#openDialogs) {
                console.debug('dialog: is open:', openDialog);
                document.getElementById(openDialog).style.zIndex = this.baseIndex + i++;
            }
        } else {
            // Add dialog to top (end of array), set z-index and make visible
            this.#openDialogs.push(idToOpen);
            dialogToOpen.style.zIndex = this.baseIndex + this.#openDialogs.indexOf(idToOpen);
            dialogToOpen.classList.remove('overlay-hidden');
        }
    }

    /**
     * Close a specific dialog
     * @param {string} idToClose HTML id of dialog element
     */
    close(idToClose) {
        console.debug('dialog: close:', idToClose);

        // Hide closed dialog
        document.getElementById(idToClose).classList.add('overlay-hidden');

        // Remove closed dialog from array
        this.#openDialogs = this.#openDialogs.filter(id => id !== idToClose);

        // Update z-index for open dialogs
        let zIndex = 0;
        for (const id of this.#openDialogs) {
            document.getElementById(id).style.zIndex = this.baseIndex + zIndex++;
        }
    }

    /**
     * Close top dialog
     */
    closeTop() {
        if (this.#openDialogs.length > 0) {
            this.close(this.#openDialogs.pop());
        }
    }

    isOpen(id) {
        return !document.getElementById(id).classList.contains('overlay-hidden');
    }

}

const dialogs = new Dialogs();

document.addEventListener('DOMContentLoaded', () => {
    // Dialog open buttons
    for (const elem of document.getElementsByClassName('dialog-overlay')) {
        const openButton = document.getElementById('open-' + elem.id);
        if (openButton === null) {
            continue;
        }
        const id = elem.id;
        openButton.addEventListener('click', () => dialogs.open(id));
    }

    // Dialog close buttons
    for (const elem of document.getElementsByClassName('dialog-close-button')) {
        const id = elem.dataset.for;
        if (id === undefined) {
            console.warn('Dialog close button has no data-for attribute');
            continue;
        }
        elem.addEventListener('click', () => dialogs.close(id));
    }
});
