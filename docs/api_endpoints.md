# PG Connect: Complete REST API Documentation

Base URL: `http://localhost:5000/api`

All protected endpoints require an `Authorization: Bearer <access_token>` header.

---

## 1. Authentication & Identity (`/api/auth`)

### Register User
- **Method:** `POST`
- **Route:** `/api/auth/register`
- **Access:** Public
- **Request Body (Tenant):**
```json
{
  "email": "user@example.com",
  "password": "Password@123",
  "full_name": "Kowshik V",
  "phone": "+919876543210",
  "role": "TENANT",
  "emergency_contact_name": "Parent",
  "emergency_contact_phone": "+919876543219",
  "emergency_contact_relation": "Father",
  "id_proof_type": "Aadhaar Card",
  "id_proof_number_masked": "XXXX-XXXX-1234"
}
```
- **Response:** `201 Created` with `access_token`, `refresh_token`, and user profile.

### Sign In
- **Method:** `POST`
- **Route:** `/api/auth/login`
- **Access:** Public
- **Request Body:**
```json
{
  "email": "owner.rajesh@pgconnect.com",
  "password": "Owner@12345"
}
```
- **Response:** `200 OK` with JWT tokens and role payload.

### Current User Profile
- **Method:** `GET`
- **Route:** `/api/auth/me`
- **Access:** Authenticated (Any role)
- **Response:** `200 OK` with user details.

---

## 2. Properties & Discovery (`/api/properties`)

### Search Accommodations
- **Method:** `GET`
- **Route:** `/api/properties/search`
- **Query Params:** `city`, `locality`, `gender` (BOYS/GIRLS/CO_ED), `sharing` (SINGLE/DOUBLE/TRIPLE), `min_rent`, `max_rent`, `has_ac`, `has_wifi`, `verified_only`, `page`, `per_page`
- **Access:** Public
- **Response:** `200 OK` with paginated property cards and live bed vacancy metrics.

### Property Details
- **Method:** `GET`
- **Route:** `/api/properties/<int:id>`
- **Access:** Public
- **Response:** `200 OK` with full property data, rooms, physical bed states, food schedule, and facilities.

### Compare Properties
- **Method:** `GET`
- **Route:** `/api/properties/compare?ids=1,2,3`
- **Access:** Public
- **Response:** `200 OK` with array of property objects for side-by-side evaluation.

### Register New Property
- **Method:** `POST`
- **Route:** `/api/properties`
- **Access:** OWNER, SUPER_ADMIN
- **Response:** `201 Created`

---

## 3. Rooms and Physical Beds (`/api`)

### Create Room with Physical Beds
- **Method:** `POST`
- **Route:** `/api/properties/<int:property_id>/rooms`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Request Body:**
```json
{
  "room_number": "205",
  "floor_number": 2,
  "sharing_type": "DOUBLE",
  "monthly_rent_per_bed": 10500.00,
  "security_deposit_per_bed": 20000.00,
  "has_ac": true,
  "has_attached_bathroom": true
}
```
- **Response:** `201 Created` (auto-initializes Bed A and Bed B as `AVAILABLE`).

### Update Bed Status
- **Method:** `PATCH`
- **Route:** `/api/beds/<int:bed_id>/status`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Request Body:** `{"status": "MAINTENANCE", "notes": "Repairs ongoing"}`
- **Response:** `200 OK`

---

## 4. Bookings & Concurrency Engine (`/api/bookings`)

### Submit Booking Request
- **Method:** `POST`
- **Route:** `/api/bookings`
- **Access:** TENANT
- **Request Body:**
```json
{
  "property_id": 1,
  "room_id": 1,
  "bed_id": 1,
  "preferred_move_in_date": "2026-12-01"
}
```
- **Response:** `201 Created` (`status: "PENDING"`)

### Approve Booking (Pessimistic Row Lock & 48h Reservation)
- **Method:** `POST`
- **Route:** `/api/bookings/<int:id>/approve`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Response:** `200 OK` (`bed.status -> "RESERVED"`, `reservation_expires_at = now + 48h`)

### Reject Booking
- **Method:** `POST`
- **Route:** `/api/bookings/<int:id>/reject`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Response:** `200 OK` (Releases bed if reserved)

---

## 5. Tenant Check-In, Check-Out & Visitors (`/api/tenants`)

### Check-In Tenant
- **Method:** `POST`
- **Route:** `/api/tenants/check-in`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Request Body:**
```json
{
  "user_id": 4,
  "bed_id": 1,
  "monthly_rent_agreed": 14500.00,
  "security_deposit_paid": 25000.00,
  "check_in_date": "2026-11-11"
}
```
- **Response:** `201 Created` (`bed.status -> "OCCUPIED"`, generates deposit and first month invoice)

### Check-Out Tenant
- **Method:** `POST`
- **Route:** `/api/tenants/allocations/<int:id>/check-out`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Response:** `200 OK` (`bed.status -> "AVAILABLE"`, settles deposit refund)

---

## 6. Financial Ledger & Invoicing (`/api/finance`)

### Generate Monthly Invoice
- **Method:** `POST`
- **Route:** `/api/finance/invoices`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Request Body:** `{"allocation_id": 1, "billing_month": 11, "billing_year": 2026, "electricity_charges": 450}`
- **Response:** `201 Created`

### Record Rent Payment
- **Method:** `POST`
- **Route:** `/api/finance/payments`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Request Body:**
```json
{
  "invoice_id": 1,
  "amount": 14950.00,
  "payment_method": "UPI",
  "transaction_reference": "UPI/604512349081"
}
```
- **Response:** `201 Created` (updates invoice status to `PAID` or `PARTIALLY_PAID`)

### Property Financial Summary
- **Method:** `GET`
- **Route:** `/api/finance/summary/property/<int:id>`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Response:** `200 OK` with real billed, collected, expenses, and occupancy metrics.

---

## 7. Reports & Documents (`/api/reports`)

### Download Official PDF Rent Receipt
- **Method:** `GET`
- **Route:** `/api/reports/invoices/<int:id>/pdf`
- **Access:** Tenant owning invoice, Property Owner, Super Admin
- **Response:** Binary PDF stream (`Receipt_INV-XXXXX.pdf`) generated via ReportLab.

### Export Property Financial Excel Workbook
- **Method:** `GET`
- **Route:** `/api/reports/properties/<int:id>/excel`
- **Access:** OWNER, SUPER_ADMIN
- **Response:** Binary Excel spreadsheet generated via OpenPyXL / Pandas.

---

## 8. Governance & Administration (`/api/admin`)

### Platform Analytics
- **Method:** `GET`
- **Route:** `/api/admin/analytics`
- **Access:** SUPER_ADMIN
- **Response:** Real query metrics for users, properties, revenue, and active tenancies.

### Property Verification
- **Method:** `POST`
- **Route:** `/api/admin/properties/<int:id>/verify`
- **Access:** SUPER_ADMIN
- **Request Body:** `{"decision": "APPROVE"}` or `{"decision": "REJECT", "reason": "Missing documents"}`
- **Response:** `200 OK`
