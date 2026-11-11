#!/usr/bin/env bash
# PG Connect — database verification (server, migrations, exact row counts, ORM round-trip).
#
#   bash docs/kowshik-dev/scripts/verify-db.sh
#
# Override anything that differs on your machine:
#   CONTAINER=pgconnect-mysql DB_NAME=pg_connect_db DB_USER=root DB_PASSWORD=password bash ...
set -u

CONTAINER="${CONTAINER:-pgconnect-mysql}"
DB_NAME="${DB_NAME:-pg_connect_db}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-password}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

say() { printf '\n== %s\n' "$1"; }

say "container"
docker ps --filter "name=$CONTAINER" --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}' \
  || { echo "container '$CONTAINER' not running — docker start $CONTAINER"; exit 1; }

say "server + sql_mode"
docker exec "$CONTAINER" mysql -u"$DB_USER" -p"$DB_PASSWORD" -N \
  -e "SELECT VERSION(), @@sql_mode;" 2>/dev/null

say "migration state"
docker exec "$CONTAINER" mysql -u"$DB_USER" -p"$DB_PASSWORD" -N \
  -e "SELECT version_num FROM $DB_NAME.alembic_version;" 2>/dev/null

say "table count"
docker exec "$CONTAINER" mysql -u"$DB_USER" -p"$DB_PASSWORD" -N \
  -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME';" 2>/dev/null

say "exact row counts"
docker exec "$CONTAINER" mysql -u"$DB_USER" -p"$DB_PASSWORD" -N -e "
  USE $DB_NAME;
  SELECT 'users',COUNT(*) FROM users UNION ALL SELECT 'owner_profiles',COUNT(*) FROM owner_profiles
  UNION ALL SELECT 'pg_properties',COUNT(*) FROM pg_properties UNION ALL SELECT 'rooms',COUNT(*) FROM rooms
  UNION ALL SELECT 'beds',COUNT(*) FROM beds UNION ALL SELECT 'bookings',COUNT(*) FROM bookings
  UNION ALL SELECT 'rent_invoices',COUNT(*) FROM rent_invoices UNION ALL SELECT 'payments',COUNT(*) FROM payments
  UNION ALL SELECT 'expenses',COUNT(*) FROM expenses UNION ALL SELECT 'complaints',COUNT(*) FROM complaints
  UNION ALL SELECT 'room_allocations',COUNT(*) FROM room_allocations UNION ALL SELECT 'reviews',COUNT(*) FROM reviews
  UNION ALL SELECT 'visitor_logs',COUNT(*) FROM visitor_logs UNION ALL SELECT 'wishlists',COUNT(*) FROM wishlists
  UNION ALL SELECT 'manager_assignments',COUNT(*) FROM manager_assignments
  UNION ALL SELECT 'property_verifications',COUNT(*) FROM property_verifications
  UNION ALL SELECT 'food_menus',COUNT(*) FROM food_menus
  UNION ALL SELECT 'audit_logs',COUNT(*) FROM audit_logs;" 2>/dev/null

say "ORM round-trip (SELECT 1, bcrypt verify, relationship traversal)"
cd "$REPO_ROOT" || exit 1
PYTHONPATH=backend .venv/bin/python - <<'PY' 2>&1 | tail -12
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.property import PGProperty
import re
app = create_app("development")
with app.app_context():
    print("uri     :", re.sub(r"://([^:]+):[^@]*@", r"://\1:***@", app.config["SQLALCHEMY_DATABASE_URI"]))
    print("select 1:", db.session.execute(db.text("SELECT 1")).scalar())
    u = User.query.filter_by(email="owner.rajesh@pgconnect.com").first()
    print("owner   :", u.id, u.email, u.role, "| password ok:", u.check_password("Owner@12345"))
    p = PGProperty.query.first()
    print("property:", p.id, p.name, "| owner_profile:", p.owner_profile.business_name, "| rooms:", len(p.rooms))
PY

say "HTTP health"
curl -s "${API_BASE:-http://127.0.0.1:5000}/api/health" | jq -c . 2>/dev/null || echo "(app not reachable — start it with: .venv/bin/python backend/run.py)"
