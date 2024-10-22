class Theater {
    #stillCount = 0;
    #timerId = null;
    #listenerFunction = null;

    constructor() {
        eventBus.subscribe(MusicEvent.SETTINGS_LOADED, () => this.#onSettingChange());
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('settings-theater').addEventListener('input', () => this.#onSettingChange());
        });
    }

    #checkStill() {
        console.debug('theater: timer', this.#stillCount);
        this.#stillCount++;

        if (this.#stillCount > 10) {
            this.activate();
        }
    }

    #onMove() {
        // if stillCount is not higher than 10, theater mode was never activated
        if (this.#stillCount > 10) {
            this.deactivate()
        }
        this.#stillCount = 0;
    }

    #onSettingChange() {
        const enabled = document.getElementById('settings-theater').checked;

        if (this.#timerId) {
            console.debug('theater: unregistered timer');
            clearInterval(this.#timerId);
            this.#timerId = null;
        }

        if (this.#listenerFunction) {
            console.debug('theater: unregistered listener');
            document.removeEventListener('pointermove', this.#listenerFunction);
            this.#listenerFunction = null;
        }

        if (enabled) {
            console.debug('theater: registered timer and listener');
            this.#timerId = setInterval(() => this.#checkStill(), 1000);
            this.#listenerFunction = () => this.#onMove();
            document.addEventListener('pointermove', this.#listenerFunction);
            return;
        }
    }

    activate() {
        document.getElementsByTagName('body')[0].classList.add('theater');
    }

    deactivate() {
        document.getElementsByTagName('body')[0].classList.remove('theater');
    }
}

const theater = new Theater();
