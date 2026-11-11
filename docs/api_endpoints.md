# PG Connect: Complete REST API Documentation

Base URL: `http://localhost:5000/api`

All protected endpoints require an `Authorization: Bearer <access_token>` header. Role authorization is strictly enforced on the backend.

---

## 1. Authentication & Identity (`/api/auth`)

### Register User (Privacy Preserving: No Aadhaar or PAN)
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
  "college_or_company_name": "Infosys Ltd"
}
```
- **Request Body (Owner):**
```json
{
  "email": "owner@example.com",
  "password": "Password@123",
  "full_name": "Owner Name",
  "phone": "+919876543211",
  "role": "OWNER",
  "business_name": "Sharma Hospitality Stays"
}
```
- **Response:** `201 Created` with `access_token`, `refresh_token`, and user profile (no government identity numbers collected or returned).

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
- **Query Params:** `city`, `locality`, `gender` (BOYS/GIRLS/CO_ED), `sharing` (SINGLE/DOUBLE/TRIPLE), `min_rent`, `max_rent`, `has_ac`, `has_wifi`, `has_food` (true/false), `verified_only` (true/false), `page`, `per_page`
- **Access:** Public
- **Response:** `200 OK` with paginated property cards, facilities, and real-time bed vacancy metrics.

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

### Register New Property (Map Coordinates Required)
- **Method:** `POST`
- **Route:** `/api/properties`
- **Access:** OWNER, SUPER_ADMIN
- **Request Body:** Requires `name`, `property_type`, `address_line1`, `locality`, `city`, `state`, `pincode`, `latitude`, `longitude`, `description`. Coordinates must be non-zero and within valid geographical ranges.
- **Response:** `201 Created` (Submitted for admin verification).

---

## 3. Maps & Geographic Endpoints (`/api/maps`)

### Public Verified Map Markers
- **Method:** `GET`
- **Route:** `/api/maps/markers`
- **Query Params:** `city`, `locality`, `gender`
- **Access:** Public
- **Filter:** Returns only `is_active=True` and `is_verified=True` properties.
- **Response:** `200 OK` with array of verified markers.

### Owner Properties Map Markers
- **Method:** `GET`
- **Route:** `/api/maps/owner-properties`
- **Access:** OWNER, SUPER_ADMIN
- **Filter:** Returns all active properties belonging to the authenticated owner (including pending-verification properties).
- **Response:** `200 OK` with array of owner markers.

### Nearby Discovery
- **Method:** `GET`
- **Route:** `/api/maps/nearby?lat=12.9352&lng=77.6245&radius=10`
- **Access:** Public
- **Response:** `200 OK` with distance-sorted list of verified properties within radius.

---

## 4. Rooms and Physical Beds (`/api`)

### Create Room with Physical Beds
- **Method:** `POST`
- **Route:** `/api/properties/<int:property_id>/rooms`
- **Access:** OWNER, MANAGER, SUPER_ADMIN (Verifies property access)
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
- **Response:** `201 Created` (auto-initializes physical beds based on sharing type).

### Update Bed Status
- **Method:** `PATCH`
- **Route:** `/api/beds/<int:bed_id>/status`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Request Body:** `{"status": "MAINTENANCE", "notes": "Repairs ongoing"}`
- **Response:** `200 OK`

---

## 5. Bookings & Concurrency Engine (`/api/bookings`)

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
  "preferred_move_in_date": "2026-12-01",
  "sharing_type": "DOUBLE"
}
```
- **Response:** `201 Created` (`status: "PENDING"`)

### Approve Booking (Pessimistic Row Lock & 48h Reservation)
- **Method:** `POST`
- **Route:** `/api/bookings/<int:id>/approve`
- **Access:** OWNER, MANAGER, SUPER_ADMIN (Ownership verified: 403 Forbidden for cross-owner)
- **Response:** `200 OK` (`bed.status -> "RESERVED"`, `reservation_expires_at = now + 48h`)

### Reject Booking
- **Method:** `POST`
- **Route:** `/api/bookings/<int:id>/reject`
- **Access:** OWNER, MANAGER, SUPER_ADMIN (Ownership verified)
- **Response:** `200 OK` (Releases reserved bed back to `AVAILABLE`)

### Cancel Booking
- **Method:** `POST`
- **Route:** `/api/bookings/<int:id>/cancel`
- **Access:** TENANT (Owning customer only)
- **Response:** `200 OK` (Releases reserved bed if previously approved)

### Trigger Reservation Expiry
- **Method:** `POST`
- **Route:** `/api/bookings/expire-reservations`
- **Access:** Public maintenance / local automation
- **Behavior:** Finds all approved bookings whose 48-hour reservation deadline has elapsed, transitions them to `EXPIRED`, and releases their reserved beds back to `AVAILABLE`. Idempotent and safe to run on demand.
- **Response:** `200 OK` with `expired_count`.

---

## 6. Tenant Check-In, Check-Out & Visitors (`/api/tenants`)

### Check-In Tenant
- **Method:** `POST`
- **Route:** `/api/tenants/check-in`
- **Access:** OWNER, MANAGER, SUPER_ADMIN (Verifies property access)
- **Validation:**
  - Validates booking status is `APPROVED`.
  - Validates bed, room, and property relationships.
  - Ensures a `RESERVED` bed belongs strictly to the checking-in customer.
  - Prevents duplicate active allocations.
- **Request Body:**
```json
{
  "user_id": 4,
  "bed_id": 1,
  "monthly_rent_agreed": 14500.00,
  "security_deposit_paid": 25000.00,
  "check_in_date": "2026-11-11",
  "booking_id": 1
}
```
- **Response:** `201 Created` (`bed.status -> "OCCUPIED"`, `booking.status -> "COMPLETED"`)

### Check-Out Tenant
- **Method:** `POST`
- **Route:** `/api/tenants/allocations/<int:id>/check-out`
- **Access:** OWNER, MANAGER, SUPER_ADMIN
- **Response:** `200 OK` (`bed.status -> "AVAILABLE"`, settles deposit refund)

---

## 7. Financial Ledger & Invoicing (`/api/finance`)

### Generate Monthly Invoice
- **Method:** `POST`
- **Route:** `/api/finance/invoices`
- **Access:** OWNER, MANAGER, SUPER_ADMIN (Verifies property access)
- **Request Body:** `{"allocation_id": 1, "billing_month": 11, "billing_year": 2026, "electricity_charges": 450}`
- **Response:** `201 Created`

### Record Rent Payment
- **Method:** `POST`
- **Route:** `/api/finance/payments`
- **Access:** OWNER, MANAGER (with payment permission), SUPER_ADMIN
- **Request Body:**
```json
{
  "invoice_id": 1,
  "amount": 14950.00,
  "payment_method": "UPI",
  "transaction_reference": "UPI/604512349081"
}
```
- **Response:** `201 Created`

### Property Financial Summary
- **Method:** `GET`
- **Route:** `/api/finance/summary/property/<int:id>`
- **Access:** OWNER, MANAGER, SUPER_ADMIN (Verifies property access)
- **Response:** `200 OK` with real billed, collected, expenses, and occupancy metrics.

---

## 8. Reports & Documents (`/api/reports`)

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

## 9. Governance & Administration (`/api/admin`)

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
