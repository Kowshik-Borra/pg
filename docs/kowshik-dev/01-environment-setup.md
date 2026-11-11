# PG Connect — Local Environment Setup (Linux)

Repo: `https://github.com/Kowshik-Borra/pg`
This copy: `~/personal/pg-connect` · set up 2026-11-11 on Ubuntu, Python 3.12.3
The upstream README is Windows-11 oriented; this file records the Linux path that actually works **here**.

---

## 1. What runs where

| Component | Location | Notes |
|---|---|---|
| Flask app (API + static frontend) | `http://127.0.0.1:5000` | one process, debug on |
| MySQL 8.0.46 | `127.0.0.1:3307` | Docker container `pgconnect-mysql`, named volume `pgconnect-mysql-data` |
| Virtualenv | `~/personal/pg-connect/.venv` | Python 3.12.3 |
| App log | `/tmp/opencode/pgconnect-server.log` | `nohup` background process |

Docker maps **3307 → 3306** because host port 3306 is already claimed inside this machine's Docker network
namespace (host `ss` shows it free; docker refuses the bind). Other containers on this box were left untouched.

---

## 2. Day-to-day commands

```bash
cd ~/personal/pg-connect

# database
docker start pgconnect-mysql          # docker stop pgconnect-mysql to halt
docker exec pgconnect-mysql mysql -uroot -ppassword -e "SELECT COUNT(*) FROM pg_connect_db.users"

# app
.venv/bin/python backend/run.py       # foreground
pkill -f "backend/run.py"             # stop it

# tests (in-memory SQLite via TestingConfig — never touches MySQL)
.venv/bin/python -m pytest -q         # 21 passed
```

---

## 3. First-time reproduction (already done on this machine)

```bash
git clone https://github.com/Kowshik-Borra/pg.git ~/personal/pg-connect
cd ~/personal/pg-connect
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt

docker run -d --name pgconnect-mysql \
  -v pgconnect-mysql-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=<your-local-db-password> \
  -e MYSQL_DATABASE=pg_connect_db \
  -p 127.0.0.1:3307:3306 --restart unless-stopped \
  mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

FLASK_APP=backend/run.py .venv/bin/python -m flask db upgrade -d backend/migrations
.venv/bin/python backend/seed.py
.venv/bin/python backend/run.py
```

Then verify with `scripts/verify-db.sh` and `scripts/readcheck.sh` (see `02-database-verification.md`).

---

## 4. ⚠ Never run `docs/pg_connect_schema.sql` against a database you care about

That file **hardcodes `USE pg_connect_db;` on line 8 and drops all 26 tables before recreating them**. It is
not isolated by the database you pass on the command line — the embedded `USE` wins. Running it emptied this
installation during the audit (see `AUDIT-021`).

Use Alembic instead. It produces an equivalent schema (verified: zero column or type differences):

```bash
FLASK_APP=backend/run.py .venv/bin/python -m flask db upgrade -d backend/migrations
```

If the database is ever emptied and the tables survive, the recovery is:

```bash
FLASK_APP=backend/run.py .venv/bin/python -m flask db upgrade -d backend/migrations
.venv/bin/python backend/seed.py          # idempotent; safe to re-run
```

---

## 5. Local deviations from upstream

- `.env` and `backend/.env` were edited: `MYSQL_PORT=3306 → 3307`, and `DATABASE_URL` host
  `localhost → 127.0.0.1:3307`. Both files are **git-tracked**, so `git status` shows them modified.
  Do not commit them back.
- No SQLite fallback exists at runtime — `config.py` raises if `DATABASE_URL` starts with `sqlite`.
  Tests use `TestingConfig` in-memory SQLite only.
- Seed data is thinner than the UI implies: `bookings`, `visitor_logs` and `property_photos` are empty
  by design (`AUDIT-020`).

---

## 6. Security findings affecting setup (full list in `03-security-audit-gate5.md`)

1. **Secrets committed to the public repository.** `.env` and `backend/.env` are tracked in git and contain
   `SECRET_KEY`, `JWT_SECRET_KEY` and MySQL credentials. A token signed with the published key is accepted as
   Super Admin — proven, `200` on `/api/admin/analytics`. Keys must be rotated and the files untracked.
2. `.gitignore` covers `.env.local` / `.env.*.local` but not `.env` itself — the root cause of (1).
3. Demo credentials are hardcoded in `frontend/pages/login.html` with one-click fill buttons, and published in
   README §3.
