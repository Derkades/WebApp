class CSRF {
    csrfToken;

    constructor() {
        // Initial CSRF token is supplied using hidden page element
        this.csrfToken = document.getElementById('csrf-token').textContent;
    }

    /**
     * @returns {string} CSRF token
     */
    getToken() {
        return this.csrfToken;
    }

    async update() {
        const response = await fetch('/get_csrf');
        checkResponseCode(response);
        const json = await response.json();
        this.csrfToken = json.token;
    }
}

const csrf = new CSRF();

document.addEventListener('DOMContentLoaded', () => {
    setInterval(() => csrf.update(), 15*60*1000);
});
