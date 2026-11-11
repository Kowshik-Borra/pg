"""
PG Connect Database Health and Diagnostics Utility
Usage: python backend/check_db.py
"""
import os
import sys
import urllib.parse
from dotenv import load_dotenv

# Load environment
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(root_dir, ".env"))
load_dotenv(os.path.join(root_dir, "backend", ".env"))
load_dotenv()

import pymysql

host = os.getenv("MYSQL_HOST", "localhost")
port = int(os.getenv("MYSQL_PORT", "3306"))
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "password")
db_name = os.getenv("MYSQL_DB", "pg_connect_db")

print("=" * 65)
print("  PG CONNECT - MYSQL DATABASE DIAGNOSTIC & REPAIR UTILITY")
print("=" * 65)
print(f"Target Host:     {host}:{port}")
print(f"Target User:     {user}")
print(f"Target Database: {db_name}")
print("-" * 65)

# Step 1: Connect to MySQL Server (Server-level)
print("[1/5] Testing MySQL Server connectivity...")
server_conn = None
try:
    server_conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset="utf8mb4",
        connect_timeout=5
    )
    print("      SUCCESS: Connected to MySQL Server!")
except pymysql.err.OperationalError as e:
    err_code, err_msg = e.args
    print(f"\n[FAIL] Could not connect to MySQL Server (Code {err_code}):")
    print(f"       {err_msg}")
    if err_code == 1045:
        print("\n--> ACTION REQUIRED: Access Denied.")
        print("    The password in your .env file does not match your MySQL root password.")
        print("    Open .env and update MYSQL_PASSWORD=your_actual_mysql_password")
    elif err_code == 2003 or "10061" in str(err_msg):
        print("\n--> ACTION REQUIRED: Connection Refused.")
        print("    MySQL Server is not running on localhost:3306.")
        print("    Start MySQL80 via Windows Services (services.msc) or run:")
        print("    net start MySQL80")
    print("=" * 65)
    sys.exit(1)
except Exception as e:
    print(f"\n[FAIL] Unexpected error: {e}")
    sys.exit(1)

# Step 2: Check / Create Database
print("[2/5] Checking database existence...")
try:
    with server_conn.cursor() as cur:
        cur.execute("SHOW DATABASES;")
        all_dbs = [r[0] for r in cur.fetchall()]
        if db_name not in all_dbs:
            print(f"      Database '{db_name}' not found. Creating '{db_name}'...")
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"      SUCCESS: Database '{db_name}' created with utf8mb4 charset.")
        else:
            print(f"      SUCCESS: Database '{db_name}' exists.")
finally:
    server_conn.close()

# Step 3: Connect directly to the database
print("[3/5] Testing database-specific connection & table count...")
expected_tables = [
    "users", "owner_profiles", "tenants", "manager_assignments", "staff",
    "pg_properties", "property_facilities", "rooms", "beds", "room_allocations",
    "property_photos", "bookings", "booking_history", "rent_invoices", "payments",
    "expenses", "security_deposits", "food_menus", "meal_logs", "complaints",
    "complaint_updates", "notifications", "reviews", "property_verifications",
    "audit_logs", "wishlists"
]

db_conn = pymysql.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=db_name,
    charset="utf8mb4"
)

existing_tables = []
with db_conn.cursor() as cur:
    cur.execute("SHOW TABLES;")
    existing_tables = [r[0] for r in cur.fetchall()]

db_conn.close()

missing_tables = [t for t in expected_tables if t not in existing_tables]
print(f"      Found {len(existing_tables)} tables in '{db_name}'.")

# Step 4: Ensure all tables exist using SQLAlchemy create_all
print("[4/5] Verifying schema completeness...")
if missing_tables:
    print(f"      Missing tables ({len(missing_tables)}): {', '.join(missing_tables[:6])}...")
    print("      Creating missing tables via SQLAlchemy metadata...")
    from app import create_app
    from app.extensions import db
    app = create_app("development")
    with app.app_context():
        db.create_all()
    print("      SUCCESS: Missing tables created safely!")
else:
    print("      All 26 expected application tables are present and verified.")

# Step 5: Test SQLAlchemy ORM session
print("[5/5] Testing SQLAlchemy 2.0 ORM session and query execution...")
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app("development")
with app.app_context():
    user_count = User.query.count()
    print(f"      SUCCESS: SQLAlchemy session active. Current users in DB: {user_count}")

print("=" * 65)
print("  ALL DATABASE CHECKS PASSED - MYSQL IS FULLY OPERATIONAL!")
print("=" * 65)

