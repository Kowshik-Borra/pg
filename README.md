# PG Connect
## Online PG Discovery, Vacancy Tracking, Booking and Management Platform

PG Connect is a centralized, production-quality web platform connecting accommodation seekers with verified Paying Guest (PG) owners and managers.

It solves the primary friction points in the PG rental market:
1. **For Accommodation Seekers:** Eliminates inaccurate vacancy indications, opaque pricing, and misleading facilities by providing real-time physical-bed-level vacancy tracking, side-by-side property comparison, verified resident reviews, and direct Google Maps navigation.
2. **For PG Owners & Managers:** Replaces manual registers and paper record keeping with an integrated business management system covering property units, physical beds, tenant check-in/check-out, monthly rent invoicing, late fee calculation, ReportLab PDF receipts, OpenPyXL financial Excel exports, food menu scheduling, and maintenance ticketing.

---

## 1. Technology Stack

- **Backend:** Python 3.10+ (tested on Python 3.14), Flask Application Factory, Flask Blueprints, SQLAlchemy 2.0 ORM, Flask-Migrate (Alembic), PyMySQL driver, Flask-JWT-Extended, Flask-CORS, bcrypt password hashing.
- **Database:** MySQL 8.0 (mandatory production & development database with complete schema DDL `docs/pg_connect_schema.sql` and InnoDB engine). SQLite is disabled in application runtime to eliminate silent fallback.
- **Frontend:** HTML5, CSS3 (Custom design system adhering to strict UI/UX guidelines), Vanilla JavaScript (Modular ES6 controllers), Bootstrap 5.3, Chart.js (financial and occupancy analytics), Leaflet with OpenStreetMap.
- **Document & Reporting Engines:** ReportLab (computer-generated official PDF rent receipts), Pandas and OpenPyXL (property financial spreadsheets).
- **Testing & QA:** pytest 9.2 automated test suite (19 tests covering all core workflows and negative authorization boundaries).

---

## 2. Key Architecture & Business Logic Enhancements

### 2.1 MySQL 8.0 Enforced Runtime
- SQLite fallback has been completely removed from application runtime. Normal application startup strictly requires valid MySQL credentials.
- Test suites run against an isolated test environment with explicit safeguards preventing destructive teardown against development or production databases.

### 2.2 Role Dashboards Separated from Public Site
- Distinct, dedicated application shells for each authenticated role (Super Admin, Owner, Manager, Tenant).
- The public website navbar is completely excluded from dashboard layouts.
- Navigation utilizes dedicated role-specific sidebars (with mobile off-canvas drawers) and topbars.
- Dashboards render only **one selected module at a time** (Overview, Properties, Map, Rooms & Beds, Bookings, Residents, Invoices, Expenses, Food Menus, Complaints), eliminating crowded multi-tab views.

### 2.3 Interactive Property Registration Map
- Property registration modal incorporates an interactive Leaflet + OpenStreetMap location picker.
- Owners can click anywhere on the map or drag the marker to pinpoint the exact latitude and longitude.
- Hardcoded coordinates (such as the previous Bengaluru default fallback) have been eliminated: valid coordinates are strictly required and verified within range (-90 to 90, -180 to 180).
- Public map markers (`/api/maps/markers`) exclusively return active and admin-verified properties.
- Owner map endpoint (`/api/maps/owner-properties`) provides owners with a geographic view of all their properties, including those pending verification.

### 2.4 User Registration Privacy Protection
- Government identity numbers (Aadhaar number, PAN card, and ID proof types) have been removed from customer and owner registration forms.
- Backend routes and schemas no longer accept or require these fields.
- Serializers and API responses do not expose identity numbers.
- Privacy policy has been updated to accurately reflect that government identity numbers are neither collected nor stored.

### 2.5 Strict Ownership and Concurrency Controls
- **Booking Approval Ownership:** Owners and managers are restricted to approving, rejecting, or managing bookings strictly for properties they own or are assigned to. Cross-owner booking modifications return HTTP 403 Forbidden.
- **Tenant Check-In Relationship Validation:** Check-in strictly verifies that the reservation matches the exact tenant, property, bed, and booking ID. A reserved bed cannot be checked in by another tenant. Bed and booking status updates execute atomically in an ACID transaction with row-level locks (`SELECT FOR UPDATE`).
- **Reservation Expiry Engine:** The `/api/bookings/expire-reservations` maintenance process automatically releases beds reserved by approved bookings whose 48-hour reservation window has elapsed, safely restoring the bed status to `AVAILABLE`.
- **Food Menu Availability Filter:** The property search endpoint correctly joins and filters properties with or without configured food menus via the `has_food` parameter.

---

## 3. Pre-Seeded Demonstration Accounts

The system includes realistic, safe, idempotent demo accounts:

| Role | Email Address | Password | Primary Capabilities |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@pgconnect.com` | `Admin@12345` | Governance, property verification queue, user moderation, system audit logs, platform analytics. |
| **PG Owner** | `owner.rajesh@pgconnect.com` | `Owner@12345` | Manage buildings, rooms, physical beds, booking approvals, rent invoices, expenses, food menus. |
| **PG Manager** | `manager.suresh@pgconnect.com` | `Manager@12345` | Resident check-in/out, payment recording, maintenance ticket resolution, visitor security log. |
| **Tenant / Resident** | `tenant.rahul@gmail.com` | `Tenant@12345` | View active stay, track bookings, download PDF rent receipts, submit maintenance complaints. |
| **Prospective Tenant** | `tenant.priya@gmail.com` | `Tenant@12345` | Search accommodations, filter by locality/budget/amenities, compare properties, request booking. |

---

## 4. Local Installation and Setup Guide (Windows 11)

### Prerequisites
- Windows 11
- Python 3.10+
- MySQL Server 8.0
- MySQL Workbench (or MySQL CLI)

### Step 1: Navigate to Workspace
```powershell
cd c:\Users\kowshik\OneDrive\Desktop\pg
```

### Step 2: Set Up Python Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Verify Python version
python --version
```

### Step 3: Install Dependencies
```powershell
pip install -r backend\requirements.txt
```

### Step 4: Configure MySQL Database and Environment
1. Ensure the MySQL 8.0 Windows service is running:
   ```powershell
   Get-Service MySQL*
   ```
2. Create the database and import the schema:
   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "CREATE DATABASE IF NOT EXISTS pg_connect_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p pg_connect_db < docs\pg_connect_schema.sql
   ```
3. Configure `.env` in the project root:
   ```ini
   FLASK_APP=backend/run.py
   FLASK_ENV=development
   SECRET_KEY=pg-connect-super-secret-key-prod-2026
   JWT_SECRET_KEY=pg-connect-jwt-token-secret-key-2026
   DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/pg_connect_db
   MYSQL_USER=root
   MYSQL_PASSWORD=YOUR_PASSWORD
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_DB=pg_connect_db
   ```

### Step 5: Run Database Migrations (Flask-Migrate / Alembic)
```powershell
$env:FLASK_APP = "backend/run.py"
.\.venv\Scripts\python.exe -m flask db upgrade -d backend/migrations
```

### Step 6: Seed Demonstration Data (Safe & Idempotent)
```powershell
.\.venv\Scripts\python.exe backend\seed.py
```
*The seed script is safe and idempotent: running it multiple times checks for existing records and avoids duplicate insertion or data loss.*

### Step 7: Start the Server
```powershell
.\.venv\Scripts\python.exe backend\run.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 5. Automated Testing

Run the automated test suite with pytest:
```powershell
.\.venv\Scripts\pytest.exe -v
```
**Test Coverage Summary (19 passing tests):**
- Authentication & RBAC (`test_auth.py`): Registration without PAN/Aadhaar, duplicate prevention, password validation, role access restrictions.
- Property & Location Management (`test_properties.py`): Property creation with valid coordinates, rejection of missing coordinates, rejection of out-of-range coordinates, rejection of `(0, 0)` placeholder, food availability filter matching, and public vs owner map marker visibility.
- Vacancy & Booking Concurrency (`test_vacancy_booking.py`): Booking request submission, owner approval bed locking (`RESERVED`), prevention of double-booking, cross-owner approval rejection (`403 Forbidden`), check-in relationship validation, active allocation duplicates prevention, and 48-hour reservation auto-expiry.
- Finance & Accounting (`test_finance.py`): Automated rent invoicing, payment recording, and balance calculation.
- Complaints & Ticketing (`test_complaints.py`): Ticket creation and status resolution workflows.

---

## 6. MySQL Connection Troubleshooting

| Error | Cause | Resolution |
| :--- | :--- | :--- |
| `Can't connect to MySQL server on 'localhost'` | MySQL service is stopped | Run `Start-Service MySQL80` or start MySQL in Windows Services (`services.msc`). |
| `Access denied for user 'root'@'localhost'` | Incorrect MySQL password | Verify password by connecting via `mysql -u root -p`. Update `DATABASE_URL` in `.env`. |
| `Unknown database 'pg_connect_db'` | Database has not been created | Run `CREATE DATABASE pg_connect_db;` in MySQL Workbench or mysql CLI. |
| Special characters in password (e.g. `@`, `#`) | URI parsing syntax error | URL-encode special characters in `DATABASE_URL` (e.g., `#` -> `%23`, `@` -> `%40`) or use `MYSQL_PASSWORD` variable. |

---

## 7. UI/UX Standards Compliance

In strict adherence to design requirements:
- **Palette:** Primary `#2563EB`, Background `#F8FAFC`, Surface `#FFFFFF`, Text `#111827`, Borders `#E2E8F0`, Success `#15803D`, Warning `#B45309`, Danger `#B91C1C`.
- **Restraints Enforced:** Zero gradients, no pill buttons, no emojis, no decorative icons everywhere, no em dashes, no AI badges, and zero fake dashboard metrics.
- **Responsiveness:** Full multi-device responsiveness with dedicated desktop sidebars and mobile off-canvas drawers.
