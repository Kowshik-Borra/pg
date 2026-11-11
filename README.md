# PG Connect
## Online PG Discovery, Vacancy Tracking, Booking and Management Platform

PG Connect is a centralized, production-quality web platform that connects people searching for Paying Guest (PG) accommodation with PG owners and managers.

It solves the two fundamental friction points in the PG rental market:
1. **For Accommodation Seekers:** Eliminates inaccurate vacancy indications, opaque pricing, and misleading facilities by providing real-time, physical-bed-level vacancy tracking, side-by-side property comparison, verified resident reviews, and direct Google Maps navigation.
2. **For PG Owners & Managers:** Replaces manual registers and paper record keeping with an integrated business management system covering property units, physical beds, tenant check-in/check-out, monthly rent invoicing, late fee calculation, ReportLab PDF receipts, OpenPyXL financial Excel exports, food menu scheduling, and maintenance ticketing.

---

## 1. Technology Stack

- **Backend:** Python 3.10+ (tested on Python 3.14), Flask Application Factory, Flask Blueprints, SQLAlchemy 2.0 ORM, Flask-Migrate (Alembic), PyMySQL driver, Flask-JWT-Extended, Flask-CORS, bcrypt password hashing.
- **Database:** MySQL 8.0 (primary target with complete schema DDL `docs/pg_connect_schema.sql` and InnoDB engine) with zero-configuration SQLite fallback (`sqlite:///pg_connect.db`) for immediate offline demonstration and automated testing.
- **Frontend:** HTML5, CSS3 (Custom design system adhering to strict UI/UX guidelines), Vanilla JavaScript (Modular ES6 controllers), Bootstrap 5.3, Chart.js (financial and occupancy analytics), Leaflet with OpenStreetMap and Google Maps navigation integration.
- **Document & Reporting Engines:** ReportLab (computer-generated official PDF rent receipts), Pandas and OpenPyXL (property financial spreadsheets).
- **Testing & QA:** pytest 9.2 automated test suite.

---

## 2. System Architecture & Physical Bed State Machine

### Real-Time Bed Vacancy Integrity
Unlike generic classified platforms where owners type in arbitrary numbers, vacancies in PG Connect are strictly derived from actual database records of physical beds.

```
[Bed Creation] -> AVAILABLE
       |
  (Owner Approves Booking)
       v
    RESERVED (48-Hour Temporary Lock via SELECT FOR UPDATE)
       |
  (Tenant Check-In)
       v
    OCCUPIED
       |
  (Tenant Check-Out)
       v
    AVAILABLE (or MAINTENANCE if repairs needed)
```

To eliminate race conditions and over-allocation, the booking approval and tenant check-in workflows execute within explicit ACID transactions utilizing InnoDB row-level locking (`with_for_update()`).

---

## 3. Pre-Seeded Demonstration Accounts

The system comes pre-seeded with realistic, clearly labeled demonstration accounts for all 4 roles:

| Role | Email Address | Password | Primary Capabilities |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@pgconnect.com` | `Admin@12345` | Governance, property verification queue, user moderation, system audit logs, platform analytics. |
| **PG Owner** | `owner.rajesh@pgconnect.com` | `Owner@12345` | Manage multiple buildings, rooms, physical beds, review booking requests, monthly rent billing, expense ledger, financial summaries, Chart.js graphs. |
| **PG Manager** | `manager.suresh@pgconnect.com` | `Manager@12345` | Operational portal, resident check-in, check-out, payment recording, maintenance ticket resolution, visitor security log. |
| **Tenant / Resident** | `tenant.rahul@gmail.com` | `Tenant@12345` | View active stay, track booking requests, download PDF rent receipts, submit maintenance complaints, verified stay review. |
| **Prospective Tenant** | `tenant.priya@gmail.com` | `Tenant@12345` | Search accommodations, filter by locality/budget/amenities, compare properties side by side, request booking. |

*Note: For convenience, the Sign In page (`/pages/login.html`) includes one-click credential autofill buttons for evaluation.*

---

## 4. Local Installation and Setup Guide

### Prerequisites
- Windows 11 / Windows 10
- Python 3.10 or higher
- MySQL Server 8.0 (Optional if using default SQLite fallback)

### Step 1: Clone or Navigate to the Workspace
```powershell
cd c:\Users\kowshik\OneDrive\Desktop\pg
```

### Step 2: Set Up Python Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate on Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Verify Python version
python --version
```

### Step 3: Install Required Dependencies
```powershell
pip install -r backend\requirements.txt
```

### Step 4: Configure the Database
The project supports both **MySQL 8.0** and **SQLite**.

#### Option A: MySQL 8.0 (Target Database)
1. Ensure your MySQL 8.0 service is started.
2. Import the schema DDL:
   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < docs\pg_connect_schema.sql
   ```
3. Update `.env` to point to MySQL:
   ```ini
   DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/pg_connect_db
   ```

#### Option B: Zero-Config Local SQLite (Ready Immediately)
The pre-configured `.env` is already configured for `sqlite:///pg_connect.db`. To seed realistic sample data:
```powershell
.\.venv\Scripts\python.exe backend\seed.py
```

### Step 5: Start the Full-Stack Application
```powershell
.\.venv\Scripts\python.exe backend\run.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 5. Automated Test Suite Execution

The automated pytest test suite verifies authentication, RBAC authorization, vacancy state transitions, double-booking prevention, invoicing, and complaint ticketing.

To run the test suite:
```powershell
.\.venv\Scripts\pytest.exe -v
```
All 10 test suites run against an isolated in-memory test database with zero external dependencies.

---

## 6. Project Structure

```
pg/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask Application Factory
│   │   ├── config.py            # Environment Configuration
│   │   ├── extensions.py        # SQLAlchemy, JWT, CORS, Migrate
│   │   ├── models/              # 26 Normalized SQLAlchemy 2.0 Models
│   │   ├── routes/              # 14 Modular Blueprints (/api/*)
│   │   ├── services/            # Business Logic & Concurrency Engine
│   │   ├── middleware/          # RBAC & Error Handling
│   │   └── utils/               # Geocoding & File Upload
│   ├── tests/                   # Automated pytest Suite
│   ├── run.py                   # Local Development & Full-Stack Server
│   ├── seed.py                  # Realistic Database Seed Script
│   └── requirements.txt         # Pinned Dependencies
│
├── frontend/
│   ├── index.html               # Public Home & Hero Discovery
│   ├── pages/                   # All Application & Dashboard Views
│   ├── css/main.css             # Restrained Custom Design System
│   ├── js/                      # Modular Vanilla JS Controllers
│   └── favicon/                 # Custom PG Connect Favicon
│
├── docs/
│   ├── pg_connect_schema.sql    # Complete MySQL 8.0 InnoDB DDL
│   ├── api_endpoints.md         # Full REST API Documentation
│   └── postman_collection.json  # Postman Test Collection
│
├── .env                         # Local Environment Configuration
├── pytest.ini                   # Test Configuration
└── README.md                    # Project Manual & Architecture Guide
```

---

## 7. UI/UX Standards Compliance

In strict adherence to design requirements:
- **Palette:** Primary `#2563EB`, Background `#F8FAFC`, Surface `#FFFFFF`, Text `#111827`, Borders `#E2E8F0`, Success `#15803D`, Warning `#B45309`, Error `#B91C1C`.
- **Restraints Enforced:** Zero gradients, no pill buttons, no fake reviews, no decorative icons, no em dashes, no AI badges, and zero artificially inflated dashboard statistics.
- **Responsiveness:** Full multi-device responsiveness across mobile, tablet, laptop, and desktop viewports.

---

## 8. Known Limitations & Future Enhancements

1. **Online Payment Gateways:** The prototype uses manual payment recording with transaction reference tracking. Direct Razorpay or Stripe webhook settlement can be integrated as an optional production upgrade.
2. **SMS Notifications:** In-app notifications are implemented. SMS integration via Twilio or Fast2SMS can be added for automated rent reminder SMS alerts.
3. **Public Deployment:** Public deployment requires connecting a verified custom domain with TLS/HTTPS certificates as per project requirements.
