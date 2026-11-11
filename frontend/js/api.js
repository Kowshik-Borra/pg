// Authenticated Fetch API Wrapper
const API = {
    getToken() {
        return localStorage.getItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN);
    },

    setSession(data) {
        if (data.access_token) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
        }
        if (data.refresh_token) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
        }
        if (data.user) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(data.user));
        }
    },

    clearSession() {
        localStorage.removeItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_DATA);
    },

    getUser() {
        const str = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_DATA);
        try {
            return str ? JSON.parse(str) : null;
        } catch (e) {
            return null;
        }
    },

    async request(endpoint, options = {}) {
        const url = endpoint.startsWith("http") ? endpoint : `${CONFIG.API_BASE_URL}${endpoint}`;
        const headers = options.headers || {};

        const token = this.getToken();
        if (token && !headers["Authorization"]) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
            headers["Content-Type"] = "application/json";
        }

        const fetchOptions = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, fetchOptions);

            // Handle blob/pdf/excel downloads
            const contentType = response.headers.get("content-type") || "";
            if (contentType.includes("application/pdf") || contentType.includes("spreadsheetml") || contentType.includes("octet-stream")) {
                if (!response.ok) {
                    throw new Error("Failed to download file.");
                }
                return await response.blob();
            }

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const message = data.error?.message || response.statusText || "Request failed.";
                const err = new Error(message);
                err.status = response.status;
                err.code = data.error?.code;
                err.details = data.error?.details;
                throw err;
            }

            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    get(endpoint, params = {}) {
        const qs = new URLSearchParams();
        Object.entries(params).forEach(([key, val]) => {
            if (val !== undefined && val !== null && val !== "") {
                qs.append(key, val);
            }
        });
        const queryStr = qs.toString();
        const url = queryStr ? `${endpoint}?${queryStr}` : endpoint;
        return this.request(url, { method: "GET" });
    },

    post(endpoint, body) {
        return this.request(endpoint, {
            method: "POST",
            body: body instanceof FormData ? body : JSON.stringify(body)
        });
    },

    put(endpoint, body) {
        return this.request(endpoint, {
            method: "PUT",
            body: body instanceof FormData ? body : JSON.stringify(body)
        });
    },

    patch(endpoint, body) {
        return this.request(endpoint, {
            method: "PATCH",
            body: body instanceof FormData ? body : JSON.stringify(body)
        });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: "DELETE" });
    }
};

