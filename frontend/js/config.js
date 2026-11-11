// PG Connect Global Configuration
const CONFIG = {
    API_BASE_URL: (function() {
        // If served directly through the Flask backend on port 5000 or production proxy
        if (window.location.port === "5000" || (!window.location.port && window.location.protocol !== "file:")) {
            return window.location.origin + "/api";
        }
        // If served through an independent frontend server (e.g. port 8000, 5500, 3000)
        const host = window.location.hostname || "127.0.0.1";
        return `http://${host}:5000/api`;
    })(),
    STORAGE_KEYS: {
        ACCESS_TOKEN: "pg_access_token",
        REFRESH_TOKEN: "pg_refresh_token",
        USER_DATA: "pg_user_data"
    }
};

