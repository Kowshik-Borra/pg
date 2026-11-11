# Database & Data-Retrieval Verification

**Date:** 2026-11-11
**Question being answered:** "The developer cannot retrieve data from the database — is the MySQL wiring broken,
or is the data simply not there?"
**Answer:** The wiring is correct. The connection, migrations, seed, ORM and every read endpoint were proven
working against a real MySQL 8.0 server. Data appears missing for two specific product reasons documented at
the end of this file (`AUDIT-019`, `AUDIT-020`).

Everything below is reproducible with `scripts/verify-db.sh` and `scripts/readcheck.sh`.

---

## 1. Server under test

```
mysql:8.0 image, server version 8.0.46
host mapping: 127.0.0.1:3307 -> container 3306
sql_mode: ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,
          ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
database: pg_connect_db (utf8mb4 / utf8mb4_unicode_ci)
app: Flask dev server on http://127.0.0.1:5000
```

`ONLY_FULL_GROUP_BY` and `STRICT_TRANS_TABLES` being **on** matters: these are the two settings that make
MySQL reject queries/inserts that SQLite happily accepts. They were active for every check below, so a passing
result here is stronger than a passing `pytest` run (the suite uses in-memory SQLite).

> Local note: host port **3307** is used because 3306 is already claimed inside this machine's Docker network
> namespace. On a normal workstation 3306 works unchanged. The container is `pgconnect-mysql` and its data now
> lives in the named volume `pgconnect-mysql-data` (originally an anonymous volume — recreated on 2026-11-11 so
> the data survives `docker rm`).

---

## 2. Migration state

```
$ docker exec pgconnect-mysql mysql -uroot -ppassword -e \
    "SELECT version_num FROM pg_connect_db.alembic_version"
002_privacy_nullable_identity
```

Both revisions applied: `001_initial_schema` (26 tables) and `002_privacy_nullable_identity`.
`SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='pg_connect_db'` → **27** (26 + `alembic_version`).

---

## 3. Row-level truth (exact `COUNT(*)`, not `information_schema` estimates)

| Table | Rows | | Table | Rows |
|---|---|---|---|---|
| users | 6 | | rent_invoices | 2 |
| owner_profiles | 2 | | payments | 1 |
| pg_properties | 2 | | expenses | 2 |
| rooms | 5 | | complaints | 1 |
| beds | 9 | | room_allocations | 2 |
| bookings | **0** | | reviews | 1 |
| visitor_logs | **0** | | wishlists | 1 |
| property_photos | **0** | | manager_assignments | 1 |
| property_verifications | **0** | | audit_logs | 8 |

The zeros are **not** a bug — see §7. `information_schema.TABLE_ROWS` reports estimates for InnoDB and is
misleading here (it claims 0 for `complaints` while the exact count is 1). Always use `COUNT(*)`.

---

## 4. ORM retrieval (no HTTP layer involved)

```python
from app import create_app
app = create_app("development")
with app.app_context():
    print(app.config["SQLALCHEMY_DATABASE_URI"])
    print(db.session.execute(db.text("SELECT 1")).scalar())
    print(User.query.filter_by(email="owner.rajesh@pgconnect.com").first().check_password("Owner@12345"))
    p = PGProperty.query.first(); print(p.name, p.owner_profile.business_name, len(p.rooms))
```

Result: URI `mysql+pymysql://root:***@127.0.0.1:3307/pg_connect_db`, `SELECT 1` → `1`, bcrypt verify → `True`,
relationship traversal (`property → owner_profile`, `property → rooms`) works.

**Aggregates and `DECIMAL` values also round-trip correctly** (the two classic MySQL-only failure modes):

```
GET /api/finance/summary/property/1
{"total_beds":6,"occupied_beds":1,"available_beds":4,"occupancy_percentage":16.7,
 "total_billed":29970.0,"total_collected":14950.0,"pending_receivables":15020.0,
 "total_expenses":21000.0,"net_operating_income":-6050.0}

GET /api/finance/invoices/property/1
{"num":"INV-202602-00101","due":14950.0,"paid":14950.0,"due_type":"number"}
```

No `Decimal`-serialization `TypeError`, no `GROUP BY` rejection.

---

## 5. Every read endpoint, as every role

```
ROLE     PATH                                     STATUS   ERROR
public   /health                                  200
public   /properties/search?per_page=50           200
public   /properties/1                            200
public   /properties/compare?ids=1,2              200
public   /properties/1/reviews                    200
public   /maps/markers                            200
public   /maps/nearby?lat=12.93&lng=77.62         200
owner    /auth/me                                 200
owner    /properties/owner/my-properties          200
owner    /bookings/property/1                     200
owner    /tenants/property/1                      200
owner    /finance/invoices/property/1             200
owner    /finance/expenses/property/1             200
owner    /finance/summary/property/1              200
owner    /complaints/property/1                   200
owner    /tenants/visitors/property/1             200
owner    /food/property/1                         200
owner    /maps/owner-properties                   200
owner    /notifications                           200
manager  /auth/me                                 200
manager  /tenants/property/1                      200
manager  /bookings/property/1                     200
manager  /finance/summary/property/1              200
tenant   /auth/me                                 200
tenant   /bookings/my-bookings                    200
tenant   /tenants/my-stay                         200
tenant   /finance/invoices/my-invoices            200
tenant   /complaints/my-complaints                 200
tenant   /wishlist                                200
tenant   /notifications                           200
tenant   /food/property/1                         200
admin    /admin/analytics                         200
admin    /admin/users                             200
admin    /admin/verifications                     200
admin    /admin/audit-logs                        200
```

**34 reads, 34 × `200`, zero `5xx`.** PDF (`/api/reports/invoices/1/pdf` → 2625 bytes, valid PDF) and Excel
(`/api/reports/properties/1/excel` → 5160 bytes, valid xlsx) generation also succeed against MySQL data.

Concrete payload spot-checks:

```
GET /api/tenants/my-stay (tenant.rahul)
{"property":"Greenview Luxury Executive PG","room":"101","bed":"Bed A","rent":14500.0}

GET /api/food/property/1
{"all_items":[{ "day_of_week":"MONDAY","meal_type":"BREAKFAST",
  "items_menu":"Idli, Vada, Sambar, Coconut Chutney, Tea / Coffee","property_id":1, ...}]}
```
28 `food_menus` rows were seeded for property 1 (7 breakfast/lunch/dinner/snacks) and all 28 are returned.

---

## 6. The README install path was reproduced — and it destroyed the database

The README tells you to do **both** a raw DDL import (`docs/pg_connect_schema.sql`) **and** Alembic migrations.
That double-provisioning is the usual place a project like this breaks, so it was tested on a database created
for the purpose (`pgc_schema_test`).

**This test wiped the working database. That is a real defect in the repository, not an accident of the test.**

```sql
-- docs/pg_connect_schema.sql, lines 7-12
CREATE DATABASE IF NOT EXISTS `pg_connect_db` CHARACTER SET utf8mb4 ...;
USE `pg_connect_db`;               -- <-- hardcoded; the client's target database is ignored
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `users`;      -- <-- and every one of the 26 tables is dropped
CREATE TABLE `users` (...);
```

`mysql -u root -p pgc_schema_test < docs/pg_connect_schema.sql` therefore did **not** create anything in
`pgc_schema_test`; the embedded `USE` redirected the whole script to `pg_connect_db`, where it dropped and
recreated all 26 tables. MySQL's binary log confirms the mechanism — 26 `DROP TABLE IF EXISTS` events followed
by `CREATE TABLE` events, and **zero** `DELETE`/`TRUNCATE` events anywhere:

```
$ SHOW BINLOG EVENTS IN 'binlog.000002'   # filtered to DDL
71476   DROP TABLE IF EXISTS `alembic_version`
...      x26 tables dropped, then recreated
166254  CREATE TABLE ...
```

The app then behaves exactly like the reported symptom: it connects, `/api/health` says `"database":"connected"`,
every endpoint answers `200`, and every list is empty. **No error, no warning, exit code 0.**

Recovery is trivial because the seed is deterministic:

```bash
cd ~/personal/pg-connect
FLASK_APP=backend/run.py .venv/bin/python -m flask db upgrade -d backend/migrations
.venv/bin/python backend/seed.py
```

That was executed after the incident: `users 5, properties 2, rooms 5, beds 9, invoices 2, allocations 2,
food_menus 28`, and the 34-endpoint smoke test returned `failures: 0`. A fresh backup was taken to
`/tmp/opencode/pgconnect-postsetup-backup.sql` (22 `INSERT` blocks).

> **Rule for anyone touching this repo:** never run `docs/pg_connect_schema.sql` against a database you care
> about, and never point it at a different database expecting isolation — it will clear `pg_connect_db`.
> This is filed as **AUDIT-021 (High)** in the security audit.

**Why the two provisioning steps coexist at all:** `001_initial_schema.upgrade()` is not a real Alembic
script — it calls `db.metadata.create_all(bind=bind)`, and `create_all` is `checkfirst=True`, so it silently
skips existing tables and stamps the revision afterwards. That is why `flask db upgrade` after the raw DDL
import does not error out.

**Schema comparison, migrations-built DB vs `schema.sql`-built DB:**

- columns missing on either side: **0**
- type or nullability differences: **0**
- differences: **240 lines, all `DEFAULT` / `ON UPDATE CURRENT_TIMESTAMP` clauses** that the hand-written DDL omits.

Those defaults are filled in by SQLAlchemy on the client side, so the ORM path is unaffected (the seed above
proved it). Only raw-SQL inserts that omit `created_at`/`status` would fail — nothing in the app does that.

### Caveat worth fixing (AUDIT, Low)
`001_initial_schema` using `create_all` means:
- `downgrade()` is a no-op — you cannot roll back a schema version.
- `flask db migrate` autogenerate compares against model metadata, so it will not detect drift introduced by
  the raw `schema.sql` import.
- A real baseline script should be generated with `alembic revision --autogenerate` and then frozen.

---

## 7. Why it *looks* like the database returns nothing

### A cause that is a genuine defect — `AUDIT-019`

`frontend/pages/manager-dashboard.html` hardcodes the property id in all three of its data calls:

```
:244  const res  = await API.get("/complaints/property/1");
:269  const tRes = await API.get("/tenants/property/1");
:274  const vRes = await API.get("/tenants/visitors/property/1");
```

There is no property selector in that dashboard. If the logged-in manager is assigned to any property other
than id `1`, all three panels render empty **while the API returns `200` with data for the correct property**.
This is the most likely origin of the "cannot retrieve data" report.

Reproduce:

```bash
# manager assigned to property 1
curl -s /api/tenants/property/1 -H "Authorization: Bearer $MANAGER" | jq '.data | length'   # 1

# a manager assigned only to property 2 sees the same hardcoded call for property 1
# -> 403 (backend correctly refuses) or an empty array for a property they do own
```

### A cause that is expectation, not a defect — `AUDIT-020`

`backend/seed.py` never constructs a `Booking`, `BookingHistory`, `VisitorLog` or `PropertyPhoto`. It allocates
residents directly to beds, bypassing the booking workflow. Therefore on a freshly seeded database:

- Owner → **Bookings** tab: empty (correct — no bookings exist)
- Manager → **Visitors** table: empty (correct — no visitor logs exist)
- Public property page → **photo gallery**: empty (correct — no photos exist)
- Payments: 1 row; Reviews: 1 row; Complaints: 1 row (thin but not empty)

---

## 8. What a *real* database failure looks like (so you can tell them apart)

Pointing the app at a dead port (3399) makes it fail loudly — it never degrades to empty pages:

```
/api/health            -> 200  {"database":"unreachable: (pymysql.err.OperationalError)
                                  (2003, \"Can't connect to MySQL server on '127.0.0.1' (timed out)\")"}
/api/properties/search -> 503  {"error":{"code":"DATABASE_CONNECTION_ERROR",
                                  "details":"(2003, \"Can't connect ...\")"}}
/api/auth/login        -> 503  {"error":{"code":"DATABASE_CONNECTION_ERROR", ...}}
```

**Decision table**

| What you see | Meaning | Fix |
|---|---|---|
| `503 DATABASE_CONNECTION_ERROR` on every call | credentials / port / MySQL service | edit `.env` (`MYSQL_PASSWORD`, `MYSQL_PORT`), start MySQL |
| `1045 Access denied` | wrong MySQL password | `.env` `MYSQL_PASSWORD` / `DATABASE_URL` |
| `1049 Unknown database` | DB not created | `CREATE DATABASE pg_connect_db ...` |
| `200` but empty panels on the **manager** dashboard | hardcoded `property/1` | AUDIT-019 |
| `200` and empty **Bookings / Visitors / Photos** | nothing was seeded | AUDIT-020 |
| `200` and **every** table empty | someone re-ran `docs/pg_connect_schema.sql` | AUDIT-021 — re-run `flask db upgrade` + `seed.py` |
| `500` on `POST /api/tenants/visitors` | `datetime` not imported | AUDIT-012 (one-line fix) |

---

## 9. Reproduce all of it

```bash
cd ~/personal/pg-connect
bash docs/kowshik-dev/scripts/verify-db.sh      # server, migrations, exact counts, ORM smoke test
bash docs/kowshik-dev/scripts/readcheck.sh      # 34 read endpoints as all four roles
```

Both scripts read `API_BASE` (default `http://127.0.0.1:5000`) and the demo credentials from §3 of the README.
