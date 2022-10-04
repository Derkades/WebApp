const dialog = {
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
            const newOpenDialogs = dialog.openDialogs.filter(openDialog => openDialog !== dialogToOpen);
            newOpenDialogs.push(idToOpen);
            let i = 1;
            for (const openDialog of newOpenDialogs) {
                console.log(openDialog);
                document.getElementById(openDialog).style.zIndex = i++;
            }
            dialog.openDialogs = newOpenDialogs;
        } else {
            dialog.openDialogs.push(idToOpen);
            dialogToOpen.style.zIndex = dialog.openDialogs.length;
            dialogToOpen.classList.remove('hidden');
        }
    },
    close: (idToClose) => {
        const newOpenDialogs = [];
        for (const id of dialog.openDialogs) {
            if (idToClose === id) {
                document.getElementById(id).classList.add('hidden');
            } else {
                newOpenDialogs.push(id);
                document.getElementById(id).style.zIndex = newOpenDialogs.length;
            }
        }
        dialog.openDialogs = newOpenDialogs;
    },
};