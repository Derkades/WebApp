let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    // Prevents the default mini-infobar or install dialog from appearing on mobile
    e.preventDefault();
    // Save the event because you'll need to trigger it later.
    deferredPrompt = e;

    const no = document.getElementById('no-support');
    const yes = document.getElement
    ById('yes-support');
    yes.classList.remove('hidden');
    no.classList.add('hidden');

    document.getElementById('install-button').addEventListener('click', () => {
        deferredPrompt.prompt();
    })
});
