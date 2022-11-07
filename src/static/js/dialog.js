const dialog = {
    baseIndex: 100,
    openDialogs: [],
    registerEvents: () => {
        // Dialog open buttons
        for (const elem of document.getElementsByClassName('dialog-overlay')) {
            const openButton = document.getElementById('open-' + elem.id);
            if (openButton === null) {
                continue;
            }
            const id = elem.id;
            openButton.addEventListener('click', () => dialog.open(id));
        };

        // Dialog close buttons
        for (const elem of document.getElementsByClassName('dialog-close-button')) {
            const id = elem.dataset.for;
            if (id === undefined) {
                console.warn('Dialog close button has no data-for attribute');
                continue;
            }
            elem.addEventListener('click', () => dialog.close(id));
        }
    },
    open: (idToOpen) => {
        const dialogToOpen = document.getElementById(idToOpen);
        if (!dialogToOpen.classList.contains('dialog-overlay')) {
            throw new Error('Dialog is missing dialog-overlay class');
        }

        if (dialog.openDialogs.indexOf(idToOpen) !== -1) {
            // Already open, elevate existing dialog to top

            // Create new array with dialog to open removed, then add it on top
            const newOpenDialogs = dialog.openDialogs.filter(openDialog => openDialog !== dialogToOpen);
            newOpenDialogs.push(idToOpen);

            // Change z-index of all open dialogs
            let i = 1;
            for (const openDialog of newOpenDialogs) {
                console.log(openDialog);
                document.getElementById(openDialog).style.zIndex = dialog.baseIndex + i++;
            }

            dialog.openDialogs = newOpenDialogs;
        } else {
            // Add dialog to top (end of array), set z-index and make visible
            dialog.openDialogs.push(idToOpen);
            dialogToOpen.style.zIndex = dialog.baseIndex + dialog.openDialogs.length;
            dialogToOpen.classList.remove('hidden');
        }
    },
    close: (idToClose) => {
        // Hide closed dialog
        document.getElementById(idToClose).classList.add('hidden');

        // Remove closed dialog from array
        dialog.openDialogs = dialog.openDialogs.filter(id => id !== idToClose);

        // Update z-index for open dialogs
        for (const id of dialog.openDialogs) {
            document.getElementById(id).style.zIndex = dialog.baseIndex + dialog.openDialogs.length;
        }
    },
    closeTop: () => {
        if (dialog.openDialogs.length > 0) {
            dialog.close(dialog.openDialogs.pop());
        }
    },
};
