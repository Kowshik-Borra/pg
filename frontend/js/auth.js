// Authentication and Role Routing Controller
const Auth = {
    isAuthenticated() {
        return !!API.getToken() && !!API.getUser();
    },

    getUserRole() {
        const user = API.getUser();
        return user ? user.role : null;
    },

    getDashboardUrl(role) {
        switch (role) {
            case "SUPER_ADMIN":
                return "/pages/admin-dashboard.html";
            case "OWNER":
                return "/pages/owner-dashboard.html";
            case "MANAGER":
                return "/pages/manager-dashboard.html";
            case "TENANT":
            default:
                return "/pages/tenant-dashboard.html";
        }
    },

    requireAuth(allowedRoles = []) {
        if (!this.isAuthenticated()) {
            window.location.href = `/pages/login.html?redirect=${encodeURIComponent(window.location.pathname)}`;
            return false;
        }

        const role = this.getUserRole();
        if (allowedRoles.length > 0 && !allowedRoles.includes(role)) {
            alert(`Access restricted. Requires role: ${allowedRoles.join(" or ")}`);
            window.location.href = this.getDashboardUrl(role);
            return false;
        }

        return true;
    },

    async login(email, password) {
        const res = await API.post("/auth/login", { email, password });
        if (res.success && res.data) {
            API.setSession(res.data);
            const redirectUrl = new URLSearchParams(window.location.search).get("redirect");
            window.location.href = redirectUrl || this.getDashboardUrl(res.data.user.role);
        }
        return res;
    },

    async register(payload) {
        const res = await API.post("/auth/register", payload);
        if (res.success && res.data) {
            API.setSession(res.data);
            window.location.href = this.getDashboardUrl(res.data.user.role);
        }
        return res;
    },

    logout() {
        API.clearSession();
        window.location.href = "/pages/login.html";
    }
};
