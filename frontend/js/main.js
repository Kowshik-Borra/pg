// Common Application Utilities and Navigation Injection
document.addEventListener("DOMContentLoaded", () => {
    initHeader();
    initFooter();
    fetchUnreadNotifications();
});

function initHeader() {
    const headerContainer = document.getElementById("site-header");
    if (!headerContainer) return;

    const user = API.getUser();
    const isAuth = Auth.isAuthenticated();

    let authButtons = `
        <li class="nav-item">
            <a class="nav-link" href="/pages/login.html">Sign In</a>
        </li>
        <li class="nav-item">
            <a class="btn btn-primary ms-lg-2" href="/pages/register.html">Register</a>
        </li>
    `;

    if (isAuth && user) {
        const dashboardUrl = Auth.getDashboardUrl(user.role);
        authButtons = `
            <li class="nav-item">
                <a class="nav-link" href="${dashboardUrl}">
                    Dashboard (${user.role.replace("_", " ")})
                </a>
            </li>
            <li class="nav-item d-flex align-items-center ms-lg-2">
                <span class="badge bg-light text-dark border me-2" id="notif-badge">0</span>
                <span class="text-muted small me-3">${user.full_name}</span>
                <button class="btn btn-outline-secondary btn-sm" onclick="Auth.logout()">Sign Out</button>
            </li>
        `;
    }

    headerContainer.innerHTML = `
        <nav class="navbar navbar-expand-lg site-navbar">
            <div class="container">
                <a class="navbar-brand d-flex align-items-center" href="/">
                    <span class="navbar-brand-text">PG CONNECT</span>
                    <span class="navbar-brand-tag">Discovery & Management</span>
                </a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav" aria-controls="mainNav" aria-expanded="false" aria-label="Toggle navigation">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="mainNav">
                    <ul class="navbar-nav ms-auto align-items-lg-center">
                        <li class="nav-item">
                            <a class="nav-link" href="/pages/search.html">Explore PGs</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/pages/compare.html">Compare</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/pages/about.html">About</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/pages/contact.html">Contact</a>
                        </li>
                        ${authButtons}
                    </ul>
                </div>
            </div>
        </nav>
    `;
}

function initFooter() {
    const footerContainer = document.getElementById("site-footer");
    if (!footerContainer) return;

    footerContainer.innerHTML = `
        <footer class="site-footer">
            <div class="container">
                <div class="row g-4">
                    <div class="col-md-4">
                        <h6 class="text-dark fw-bold mb-3">PG CONNECT</h6>
                        <p class="small text-muted mb-2">
                            A centralized platform connecting accommodation seekers with verified PG owners across major urban hubs.
                        </p>
                        <p class="small text-muted">
                            Transparent vacancies, direct owner communication, real-time bed reservations, and verified facilities.
                        </p>
                    </div>
                    <div class="col-md-2 col-6">
                        <h6 class="text-dark fw-bold mb-3">Discovery</h6>
                        <ul class="list-unstyled small">
                            <li class="mb-2"><a href="/pages/search.html" class="text-muted">Find PG</a></li>
                            <li class="mb-2"><a href="/pages/search.html?gender=BOYS" class="text-muted">Boys PGs</a></li>
                            <li class="mb-2"><a href="/pages/search.html?gender=GIRLS" class="text-muted">Girls PGs</a></li>
                            <li class="mb-2"><a href="/pages/search.html?gender=CO_ED" class="text-muted">Co-Living</a></li>
                        </ul>
                    </div>
                    <div class="col-md-2 col-6">
                        <h6 class="text-dark fw-bold mb-3">For Owners</h6>
                        <ul class="list-unstyled small">
                            <li class="mb-2"><a href="/pages/register.html?role=OWNER" class="text-muted">List Property</a></li>
                            <li class="mb-2"><a href="/pages/login.html" class="text-muted">Owner Portal</a></li>
                            <li class="mb-2"><a href="/pages/about.html" class="text-muted">Verification Criteria</a></li>
                        </ul>
                    </div>
                    <div class="col-md-4">
                        <h6 class="text-dark fw-bold mb-3">Legal and Support</h6>
                        <ul class="list-unstyled small">
                            <li class="mb-2"><a href="/pages/privacy-policy.html" class="text-muted">Privacy Policy</a></li>
                            <li class="mb-2"><a href="/pages/terms-conditions.html" class="text-muted">Terms and Conditions</a></li>
                            <li class="mb-2"><a href="/pages/contact.html" class="text-muted">Contact Support</a></li>
                            <li class="mb-2 text-muted">Operational hours: Mon - Sat, 09:00 - 18:00 IST</li>
                        </ul>
                    </div>
                </div>
                <div class="border-top mt-4 pt-3 text-center small text-muted">
                    PG Connect Platform. All rights reserved. Built for professional PG discovery and operational management.
                </div>
            </div>
        </footer>
    `;
}

async function fetchUnreadNotifications() {
    if (!Auth.isAuthenticated()) return;
    try {
        const res = await API.get("/notifications");
        if (res.success && res.data) {
            const badge = document.getElementById("notif-badge");
            if (badge) {
                badge.innerText = `${res.data.unread_count} alerts`;
                if (res.data.unread_count > 0) {
                    badge.className = "badge bg-primary text-white border me-2";
                }
            }
        }
    } catch (e) {
        // Quiet fallback
    }
}

// Global Formatting Utilities
function formatCurrency(amount) {
    return "Rs. " + Number(amount || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
}
