# PG Connect — Engineering Review Pack (`docs/kowshik-dev`)

Work done on a clone of `https://github.com/Kowshik-Borra/pg` on 2026-11-11:
environment setup, database verification, a full adversarial security review, and an ordered fix plan.

Start with the **summary** below, then open whichever document matches your question.

---

## Read in this order

| File | What it answers |
|---|---|
| [`01-environment-setup.md`](01-environment-setup.md) | How to run this repo on Linux (MySQL via Docker, migrations, seed, day-to-day commands) |
| [`02-database-verification.md`](02-database-verification.md) | *"Is the database actually working, or is the data missing?"* — with row counts, 34 endpoint checks and the reproduction of the setup script that empties the DB |
| [`03-security-audit-gate5.md`](03-security-audit-gate5.md) | Full adversarial audit: 21 findings with evidence, attack scenarios and fixes |
| [`04-remediation-plan.md`](04-remediation-plan.md) | Phased fix plan with acceptance criteria and the tests to add |
| [`scripts/verify-db.sh`](scripts/verify-db.sh) | Re-runs the DB verification (server, migrations, exact counts, ORM round-trip) |
| [`scripts/readcheck.sh`](scripts/readcheck.sh) | Hits every read endpoint as all four roles; expects `failures: 0` |

---

## Summary

**The database works.** Connection, migrations, seed, ORM, aggregates, `DECIMAL` serialisation and 34 read
endpoints were all verified against a real MySQL 8.0.46 with `STRICT_TRANS_TABLES` and `ONLY_FULL_GROUP_BY`
enabled. `scripts/readcheck.sh` reports `failures: 0`.

**"I can't retrieve data" has four real causes, none of them the connection:**

1. **`docs/pg_connect_schema.sql` wipes the database** — it hardcodes `USE pg_connect_db` and drops all 26
   tables first. Running it (README Step 4) leaves a working app with empty tables, `200` responses and no
   error. This happened during the audit. **AUDIT-021 (High).**
2. **The manager dashboard hardcodes `property_id = 1`** in three calls; any manager assigned elsewhere sees
   three empty panels while the API returns data. **AUDIT-019.**
3. **The seed never creates bookings, visitor logs or property photos**, so those tables are empty by design.
   **AUDIT-020.**
4. **A genuinely wrong `.env`** produces loud `503 DATABASE_CONNECTION_ERROR`, never silence — so if it were
   the credentials, you would have seen errors, not empty pages.

**Security posture is not production ready.** The most serious item: `JWT_SECRET_KEY` is committed in `.env` in
a **public** repository, and a token forged with it was accepted as **Super Admin** (`200` on
`/api/admin/analytics`, no credentials). On top of that: four missing object-level authorization checks that
let any self-registered owner read another owner's residents' PII, evict their tenant and download their
invoices; stored XSS in every dashboard; and no token revocation on password change or suspension.

---

## Health snapshot (2026-11-11, after recovery)

```
MySQL 8.0.46 via Docker (pgconnect-mysql, volume pgconnect-mysql-data, host port 3307)
alembic: 002_privacy_nullable_identity    tables: 27

users 5 | owner_profiles 1 | pg_properties 2 | rooms 5 | beds 9
rent_invoices 2 | payments 1 | expenses 2 | room_allocations 2
complaints 1 | reviews 1 | wishlists 1 | food_menus 28
bookings 0 | visitor_logs 0 | property_photos 0     <- empty by design, AUDIT-020

pytest                    21 passed  (in-memory SQLite, isolated)
scripts/readcheck.sh      failures: 0
seed.py                   idempotent, refuses to double-seed
backup                    /tmp/opencode/pgconnect-postsetup-backup.sql
```

---

## Finding index

| Severity | Count | IDs |
|---|---|---|
| Critical | 1 | AUDIT-001 (JWT key in public repo → Super Admin forgery) |
| High | 5 | AUDIT-002, 003, 004, 005, 006 + AUDIT-021 (destructive schema script) |
| Medium | 7 | AUDIT-007 … 012, 019 |
| Low | 7 | AUDIT-013 … 018, 020 |

Verified clean: no SQL injection anywhere (all queries ORM/parameterised), booking approval does enforce
ownership, bcrypt cost 12, test suite isolated from real data.

---

## Reproduce everything

```bash
cd ~/personal/pg-connect
bash docs/kowshik-dev/scripts/verify-db.sh     # DB truth
bash docs/kowshik-dev/scripts/readcheck.sh     # 34 reads, all roles
.venv/bin/python -m pytest -q                  # 21 tests
```

Both scripts accept `API_BASE=` (default `http://127.0.0.1:5000`) so they can be pointed at any instance.
