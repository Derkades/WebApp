const CSRF_EXPIRY_MILLIS = 20*60*1000; // 20 minutes

class CSRF {
    csrfToken;
    lastTokenUpdate;

    constructor() {
        this.csrfToken = null;
        this.lastTokenUpdate = null;
    }

    /**
     * @returns {Promise<string>} CSRF token
     */
    async getToken() {

        if (this.csrfToken == null) {
            console.info('No CSRF token stored');
            await this.update();
        } else {
            const age = Date.now() - this.lastTokenUpdate;
            console.debug(`CSRF last updated ${Math.round(age/1000)} seconds ago`);
            if (age > CSRF_EXPIRY_MILLIS) {
                console.info('Stored CSRF token has expired');
                await this.update();
            }
        }

        return this.csrfToken;
    }

    async update() {
        const response = await fetch('/get_csrf');
        checkResponseCode(response);
        const json = await response.json();
        this.csrfToken = json.token;
        this.lastTokenUpdate = Date.now();
    }
}

const csrf = new CSRF();
