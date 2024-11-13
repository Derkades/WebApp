let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    // Prevents the default mini-infobar or install dialog from appearing on mobile
    e.preventDefault();

    deferredPrompt = e;

    const no = document.getElementById('no-support');
    const yes = document.getElementById('yes-support');
    yes.classList.remove('hidden');
    no.classList.add('hidden');

    document.getElementById('install-button').addEventListener('click', () => {
        deferredPrompt.prompt();
    })
});
