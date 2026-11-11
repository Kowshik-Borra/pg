# Remediation Plan — PG Connect

Derived from `03-security-audit-gate5.md` (21 findings). Ordered so that each phase removes the amplifying
factor for the next one. Every phase ends with a verification you can run, not a claim.

Nothing here has been implemented. This is a plan awaiting owner approval — and one item (rewriting git
history for the leaked keys) needs an explicit decision because the repository is public and not ours.

---

## Phase 0 — Stop the bleeding (do this before anything else)

| # | Finding | Action | Files |
|---|---|---|---|
| 1 | AUDIT-001 | Rotate `SECRET_KEY` + `JWT_SECRET_KEY`, untrack `.env` files, add `.env` to `.gitignore` | `.env`, `backend/.env`, `.gitignore` |
| 2 | AUDIT-011 | Remove the one-click demo credential buttons from the login page; make `seed.py` refuse to run outside development | `frontend/pages/login.html:51,54,60`, `backend/seed.py` |
| 3 | AUDIT-021 | Strip `CREATE DATABASE` / `USE` from `docs/pg_connect_schema.sql`; move the 26 `DROP TABLE` statements into an opt-in reset script | `docs/pg_connect_schema.sql:7-12` |

```bash
git rm --cached .env backend/.env
printf '\n# secrets\n.env\n' >> .gitignore
git commit -m "chore(security): stop tracking credentials, rotate keys"
```

**History rewrite is a separate decision.** Untracking stops future leaks; the keys stay readable in past
commits. Purging requires `git filter-repo` on a public repo — owner's call, not ours.

**Acceptance:** `git ls-files | grep -c '^\.env$'` → `0`; a token signed with the old key returns `401`.

---

## Phase 1 — Tenant isolation (the biggest correctness gap)

One shared helper, applied everywhere. The correct pattern already exists in `finance_routes.py`.

| # | Finding | Action | Files |
|---|---|---|---|
| 4 | AUDIT-006 | Registration must accept only `TENANT` and `OWNER`; `MANAGER` accounts are created by an owner/admin and bound to a `ManagerAssignment` | `auth_routes.py:22-28` |
| 5 | AUDIT-002 | Derive the property from `bed_id` / `allocation_id` inside the service and call `verify_property_access` before any read or write | `tenant_routes.py:16,51,85,129,162` |
| 6 | AUDIT-004 | Same for complaints: list and status update | `complaint_routes.py:102,112` |
| 7 | AUDIT-003 | Same for reports: invoice PDF (owner/manager path) and property Excel | `report_routes.py:11,31` |

Suggested helper (single implementation, reused):

```python
# backend/app/middleware/rbac.py
def require_property_access(property_id, perm=None):
    """Resolve the acting user from the request and assert access, or raise 403."""
    user = get_current_user()
    if not user:
        raise APIException("Authentication required.", status_code=401, code="UNAUTHORIZED")
    return verify_property_access(property_id, user, required_manager_perm=perm)
```

**Acceptance (must be automated, one test per route):**
- owner with zero properties → `403` on `GET /api/tenants/property/1`, `POST /api/tenants/check-in`,
  `POST /api/tenants/allocations/1/check-out`, `GET /api/complaints/property/1`,
  `PATCH /api/complaints/1/status`, `GET /api/reports/properties/1/excel`,
  `GET /api/reports/invoices/1/pdf`
- the owning owner → unchanged `200`/`201`
- `POST /api/auth/register {"role":"MANAGER"}` → `400`

---

## Phase 2 — Client-side compromise paths

| # | Finding | Action | Files |
|---|---|---|---|
| 8 | AUDIT-005 | Add one `escapeHtml()` helper; apply to **every** `${...}` that lands in `innerHTML` | `frontend/js/*.js`, all `frontend/pages/*.html` |
| 9 | AUDIT-014 | `after_request` security headers; a CSP without `unsafe-inline` once (8) is done | `backend/app/__init__.py` |
| 10 | AUDIT-007 | `jti` blocklist + per-user `token_version`; revoke on password change/suspend; rotate refresh tokens; add `POST /api/auth/logout` | `auth_routes.py`, `user_routes.py`, `middleware/rbac.py` |

**Acceptance:**
- complaint title `<img src=x onerror=...>` renders as literal text, no outbound request
- `curl -sI /` shows CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- change password → old access **and** old refresh → `401`

---

## Phase 3 — Correctness bugs found during the audit

| # | Finding | Action | Files |
|---|---|---|---|
| 11 | AUDIT-012 | `from datetime import datetime` (one line) + a test for visitor create/list | `tenant_routes.py:1` |
| 12 | AUDIT-009 | Derive the booking from the bed in `check_in_tenant` and always close it to `COMPLETED` | `tenant_service.py:33-99` |
| 13 | AUDIT-008 | Require `SUPER_ADMIN` on `/api/bookings/expire-reservations`; move the sweep to a scheduler | `booking_routes.py:146` |
| 14 | AUDIT-019 | Replace hardcoded `"/complaints/property/1"` etc. with the manager's selected property | `manager-dashboard.html:244,269,274` |
| 15 | AUDIT-015 | Verify reservation ownership before releasing a bed; add `FOR UPDATE` | `booking_service.py:230-241` |
| 16 | AUDIT-020 | Seed 2-3 bookings across states, one visitor log, one property photo, a few payments | `backend/seed.py` |

**Acceptance:** check-in without `booking_id` leaves the booking `COMPLETED`; expiry sweep then reports `0` and
touches nothing; a manager assigned to property 2 sees property 2's complaints.

---

## Phase 4 — Hardening

| # | Finding | Action |
|---|---|---|
| 17 | AUDIT-010 | Public search and detail-by-id must filter `is_verified == True` |
| 18 | AUDIT-013 | Per-IP + per-account login throttling, backoff, alert on repeated failures |
| 19 | AUDIT-016 | Never return exception text; `/api/health` reports `ok`/`degraded`; drop the default password in `check_db.py` |
| 20 | AUDIT-017 | Either drop `pan_number`/`aadhaar_last4` or correct the privacy policy — not both |
| 21 | AUDIT-018 | Bounding-box prefilter, cap `radius_km`, limit results; consider `ST_Distance_Sphere` |

Also worth doing, not filed as a finding:
- `001_initial_schema` should become a real generated baseline instead of `db.metadata.create_all()` so
  `downgrade()` and `flask db migrate` mean something.
- Add a `docs/kowshik-dev/scripts/` job to CI: `pytest` + `readcheck.sh` against a throwaway MySQL service.

---

## Suggested test additions (pytest)

```
tests/test_authorization.py     # one 403 assertion per property-scoped route, per phase 1
tests/test_visitors.py          # AUDIT-012 create + list + foreign-property 403
tests/test_booking_state.py     # AUDIT-009 check-in without booking_id -> COMPLETED
tests/test_tokens.py            # AUDIT-007 revocation on password change / suspension
tests/test_registration.py      # AUDIT-006 role escalation rejected
```

Target: 21 existing tests must stay green; each new file must fail before its fix and pass after.

---

## What we will NOT do without an explicit decision

1. **Rewrite git history** to purge the leaked `JWT_SECRET_KEY` / database password from the public repo.
2. **Force-push anything** to `Kowshik-Borra/pg`.
3. **Change the demo account passwords**, which are referenced by the README and the seeded data.

Everything in Phases 0-4 is local and reversible; items (1) and (3) change behaviour for whoever else uses
this repo.
