import os
from datetime import datetime, date, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models.user import User, OwnerProfile, ManagerAssignment, Staff
from app.models.property import PGProperty, PropertyPhoto, PropertyFacility
from app.models.room_bed import Room, Bed
from app.models.tenant import Tenant, RoomAllocation, VisitorLog
from app.models.booking import Booking, BookingHistory
from app.models.finance import RentInvoice, Payment, SecurityDeposit, Expense
from app.models.food import FoodMenu
from app.models.complaint import Complaint, ComplaintUpdate
from app.models.governance import Review, Wishlist, Notification, PropertyVerification, AuditLog

app = create_app(os.getenv("FLASK_ENV", "development"))

def seed_database():
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding Users...")
        # 1. Super Admin
        admin = User(
            email="admin@pgconnect.com",
            full_name="Platform Administrator",
            phone="+919876543210",
            role="SUPER_ADMIN",
            is_active=True,
            is_verified=True
        )
        admin.set_password("Admin@12345")
        db.session.add(admin)

        # 2. PG Owner
        owner_user = User(
            email="owner.rajesh@pgconnect.com",
            full_name="Rajesh Sharma",
            phone="+919811223344",
            role="OWNER",
            is_active=True,
            is_verified=True
        )
        owner_user.set_password("Owner@12345")
        db.session.add(owner_user)
        db.session.flush()

        owner_profile = OwnerProfile(
            user_id=owner_user.id,
            business_name="Sharma Hospitality & Living",
            pan_number="ABCPS1234K",
            aadhaar_last4="7890",
            is_approved=True,
            approved_by=admin.id,
            approved_at=datetime.now(timezone.utc)
        )
        db.session.add(owner_profile)
        db.session.flush()

        # 3. PG Manager
        manager_user = User(
            email="manager.suresh@pgconnect.com",
            full_name="Suresh Kumar",
            phone="+919822334455",
            role="MANAGER",
            is_active=True,
            is_verified=True
        )
        manager_user.set_password("Manager@12345")
        db.session.add(manager_user)

        # 4. Tenants
        tenant_user1 = User(
            email="tenant.priya@gmail.com",
            full_name="Priya Patel",
            phone="+919833445566",
            role="TENANT",
            is_active=True,
            is_verified=True
        )
        tenant_user1.set_password("Tenant@12345")
        db.session.add(tenant_user1)

        tenant_user2 = User(
            email="tenant.rahul@gmail.com",
            full_name="Rahul Verma",
            phone="+919844556677",
            role="TENANT",
            is_active=True,
            is_verified=True
        )
        tenant_user2.set_password("Tenant@12345")
        db.session.add(tenant_user2)
        db.session.flush()

        # Tenant Profiles
        t1 = Tenant(
            user_id=tenant_user1.id,
            emergency_contact_name="Mahesh Patel",
            emergency_contact_phone="+919988776655",
            emergency_contact_relation="Father",
            id_proof_type="Aadhaar Card",
            id_proof_number_masked="XXXX-XXXX-4589",
            college_or_company_name="Infosys Ltd"
        )
        t2 = Tenant(
            user_id=tenant_user2.id,
            emergency_contact_name="Sunita Verma",
            emergency_contact_phone="+919977665544",
            emergency_contact_relation="Mother",
            id_proof_type="Passport",
            id_proof_number_masked="P1234567X",
            college_or_company_name="Wipro Technologies"
        )
        db.session.add_all([t1, t2])
        db.session.flush()

        print("Seeding PG Properties...")
        # Property 1: Boys PG in Koramangala
        prop1 = PGProperty(
            owner_id=owner_profile.id,
            name="Greenview Luxury Executive PG",
            slug="greenview-luxury-executive-pg-bengaluru",
            property_type="BOYS",
            address_line1="#42, 5th Block, 80 Feet Road",
            address_line2="Near Sony World Signal",
            locality="Koramangala",
            city="Bengaluru",
            state="Karnataka",
            pincode="560095",
            latitude=12.9352,
            longitude=77.6245,
            contact_phone="+919811223344",
            contact_email="greenview.pg@gmail.com",
            description="Premium executive PG for working professionals and students with dedicated high-speed optical fiber Wi-Fi, daily housekeeping, 3-times hygienic meals, power backup, and round-the-clock biometric security.",
            rules="Strictly non-smoking campus. Guests permitted in lobby till 8:00 PM. Gate closes at 22:30. No alcohol consumption on premises.",
            notice_period_days=30,
            gate_closing_time="22:30",
            is_verified=True,
            is_active=True
        )
        db.session.add(prop1)
        db.session.flush()

        # Facilities for Prop 1
        fac1 = PropertyFacility(
            property_id=prop1.id,
            has_wifi=True,
            has_ac=True,
            has_washing_machine=True,
            has_parking=True,
            has_housekeeping=True,
            has_cctv=True,
            has_drinking_water=True,
            has_power_backup=True,
            has_attached_washroom=True,
            has_refrigerator=True,
            has_biometric_access=True
        )
        db.session.add(fac1)

        # Property 2: Girls PG in Indiranagar
        prop2 = PGProperty(
            owner_id=owner_profile.id,
            name="Serene Comforts PG for Women",
            slug="serene-comforts-pg-for-women-bengaluru",
            property_type="GIRLS",
            address_line1="12th Main, HAL 2nd Stage",
            address_line2="Near Indiranagar Metro Station",
            locality="Indiranagar",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
            latitude=12.9784,
            longitude=77.6408,
            contact_phone="+919811223344",
            contact_email="serene.pg@gmail.com",
            description="Safe, modern, and spacious PG accommodation for female students and corporate professionals. Located 300 meters from Indiranagar Metro Station with 24/7 female security guard, nutritious homestyle meals, and study lounges.",
            rules="Quiet study hours after 22:00. Biometric entry required. Male visitors restricted to reception area.",
            notice_period_days=30,
            gate_closing_time="22:00",
            is_verified=True,
            is_active=True
        )
        db.session.add(prop2)
        db.session.flush()

        fac2 = PropertyFacility(
            property_id=prop2.id,
            has_wifi=True,
            has_ac=True,
            has_washing_machine=True,
            has_parking=True,
            has_housekeeping=True,
            has_cctv=True,
            has_drinking_water=True,
            has_power_backup=True,
            has_attached_washroom=True,
            has_refrigerator=True,
            has_biometric_access=True
        )
        db.session.add(fac2)

        # Assign manager to Property 1
        mgr_assign = ManagerAssignment(
            manager_user_id=manager_user.id,
            property_id=prop1.id,
            assigned_by=owner_user.id,
            can_manage_payments=True,
            can_manage_complaints=True,
            is_active=True
        )
        db.session.add(mgr_assign)

        # Staff for Prop 1
        s1 = Staff(property_id=prop1.id, full_name="Ramu Gowda", role_designation="Head Cook", phone="+919100112233", salary_amount=22000.00)
        s2 = Staff(property_id=prop1.id, full_name="Sunil Das", role_designation="Housekeeping & Maintenance", phone="+919100112244", salary_amount=16000.00)
        db.session.add_all([s1, s2])

        print("Seeding Rooms and Beds...")
        # Prop 1 - Room 101: Single Sharing
        r101 = Room(
            property_id=prop1.id,
            room_number="101",
            floor_number=1,
            sharing_type="SINGLE",
            has_ac=True,
            has_attached_bathroom=True,
            monthly_rent_per_bed=14500.00,
            security_deposit_per_bed=25000.00,
            is_active=True
        )
        db.session.add(r101)
        db.session.flush()
        bed_101_a = Bed(room_id=r101.id, bed_label="Bed A", status="OCCUPIED", last_status_change=datetime.now(timezone.utc), notes="Allocated to Rahul Verma")
        db.session.add(bed_101_a)

        # Prop 1 - Room 102: Double Sharing
        r102 = Room(
            property_id=prop1.id,
            room_number="102",
            floor_number=1,
            sharing_type="DOUBLE",
            has_ac=False,
            has_attached_bathroom=True,
            monthly_rent_per_bed=9500.00,
            security_deposit_per_bed=18000.00,
            is_active=True
        )
        db.session.add(r102)
        db.session.flush()
        bed_102_a = Bed(room_id=r102.id, bed_label="Bed A", status="AVAILABLE", last_status_change=datetime.now(timezone.utc), notes="Cleaned and ready")
        bed_102_b = Bed(room_id=r102.id, bed_label="Bed B", status="AVAILABLE", last_status_change=datetime.now(timezone.utc), notes="Cleaned and ready")
        db.session.add_all([bed_102_a, bed_102_b])

        # Prop 1 - Room 103: Triple Sharing
        r103 = Room(
            property_id=prop1.id,
            room_number="103",
            floor_number=1,
            sharing_type="TRIPLE",
            has_ac=False,
            has_attached_bathroom=False,
            monthly_rent_per_bed=7500.00,
            security_deposit_per_bed=15000.00,
            is_active=True
        )
        db.session.add(r103)
        db.session.flush()
        bed_103_a = Bed(room_id=r103.id, bed_label="Bed A", status="AVAILABLE", last_status_change=datetime.now(timezone.utc))
        bed_103_b = Bed(room_id=r103.id, bed_label="Bed B", status="AVAILABLE", last_status_change=datetime.now(timezone.utc))
        bed_103_c = Bed(room_id=r103.id, bed_label="Bed C", status="MAINTENANCE", last_status_change=datetime.now(timezone.utc), notes="Mattress replacement scheduled")
        db.session.add_all([bed_103_a, bed_103_b, bed_103_c])

        # Prop 2 - Room 201: Single Sharing (Allocated to Priya Patel)
        r201 = Room(
            property_id=prop2.id,
            room_number="201",
            floor_number=2,
            sharing_type="SINGLE",
            has_ac=True,
            has_attached_bathroom=True,
            monthly_rent_per_bed=16000.00,
            security_deposit_per_bed=30000.00,
            is_active=True
        )
        db.session.add(r201)
        db.session.flush()
        bed_201_a = Bed(room_id=r201.id, bed_label="Bed A", status="OCCUPIED", last_status_change=datetime.now(timezone.utc), notes="Occupied by Priya Patel")
        db.session.add(bed_201_a)

        # Prop 2 - Room 202: Double Sharing
        r202 = Room(
            property_id=prop2.id,
            room_number="202",
            floor_number=2,
            sharing_type="DOUBLE",
            has_ac=True,
            has_attached_bathroom=True,
            monthly_rent_per_bed=10500.00,
            security_deposit_per_bed=20000.00,
            is_active=True
        )
        db.session.add(r202)
        db.session.flush()
        bed_202_a = Bed(room_id=r202.id, bed_label="Bed A", status="AVAILABLE", last_status_change=datetime.now(timezone.utc))
        bed_202_b = Bed(room_id=r202.id, bed_label="Bed B", status="AVAILABLE", last_status_change=datetime.now(timezone.utc))
        db.session.add_all([bed_202_a, bed_202_b])
        db.session.flush()

        print("Seeding Room Allocations and Invoices...")
        # Allocation 1: Rahul in Prop 1 Room 101 Bed A
        alloc1 = RoomAllocation(
            tenant_id=t2.id,
            bed_id=bed_101_a.id,
            check_in_date=date(2026, 1, 5),
            monthly_rent_agreed=14500.00,
            security_deposit_paid=25000.00,
            is_active=True
        )
        db.session.add(alloc1)
        db.session.flush()

        # Allocation 2: Priya in Prop 2 Room 201 Bed A
        alloc2 = RoomAllocation(
            tenant_id=t1.id,
            bed_id=bed_201_a.id,
            check_in_date=date(2026, 1, 10),
            monthly_rent_agreed=16000.00,
            security_deposit_paid=30000.00,
            is_active=True
        )
        db.session.add(alloc2)
        db.session.flush()

        # Security Deposit records
        sd1 = SecurityDeposit(
            tenant_id=t2.id,
            property_id=prop1.id,
            amount_deposited=25000.00,
            deposit_date=date(2026, 1, 5),
            refund_status="HELD"
        )
        sd2 = SecurityDeposit(
            tenant_id=t1.id,
            property_id=prop2.id,
            amount_deposited=30000.00,
            deposit_date=date(2026, 1, 10),
            refund_status="HELD"
        )
        db.session.add_all([sd1, sd2])

        # Rent Invoices
        inv1 = RentInvoice(
            invoice_number="INV-202602-00101",
            property_id=prop1.id,
            tenant_id=t2.id,
            allocation_id=alloc1.id,
            billing_month=2,
            billing_year=2026,
            base_rent_amount=14500.00,
            electricity_charges=450.00,
            food_charges=0.00,
            late_fee_amount=0.00,
            total_amount_due=14950.00,
            amount_paid=14950.00,
            due_date=date(2026, 2, 5),
            status="PAID"
        )
        db.session.add(inv1)
        db.session.flush()

        pay1 = Payment(
            payment_reference="PAY-202602-99881",
            invoice_id=inv1.id,
            tenant_id=t2.id,
            amount=14950.00,
            payment_method="UPI",
            transaction_reference="UPI/604512349081",
            payment_date=date(2026, 2, 4),
            status="COMPLETED",
            verified_by_user_id=manager_user.id,
            notes="Received via Google Pay"
        )
        db.session.add(pay1)

        inv2 = RentInvoice(
            invoice_number="INV-202603-00102",
            property_id=prop1.id,
            tenant_id=t2.id,
            allocation_id=alloc1.id,
            billing_month=3,
            billing_year=2026,
            base_rent_amount=14500.00,
            electricity_charges=520.00,
            food_charges=0.00,
            late_fee_amount=0.00,
            total_amount_due=15020.00,
            amount_paid=0.00,
            due_date=date(2026, 3, 5),
            status="PENDING"
        )
        db.session.add(inv2)

        print("Seeding Expenses...")
        exp1 = Expense(
            property_id=prop1.id,
            category="ELECTRICITY",
            amount=6800.00,
            expense_date=date(2026, 2, 10),
            description="BESCOM Electricity Bill for February 2026",
            recorded_by_user_id=owner_user.id
        )
        exp2 = Expense(
            property_id=prop1.id,
            category="GROCERY_FOOD",
            amount=14200.00,
            expense_date=date(2026, 2, 12),
            description="Monthly grocery and vegetables mess purchase",
            recorded_by_user_id=owner_user.id
        )
        db.session.add_all([exp1, exp2])

        print("Seeding Food Menus...")
        days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        menu_items = {
            "BREAKFAST": "Idli, Vada, Sambar, Coconut Chutney, Tea / Coffee",
            "LUNCH": "Steamed Rice, Dal Tadka, Seasonal Sabzi, Phulka Roti, Curd, Pickle",
            "EVENING_SNACKS": "Masala Chai with Samosa / Onion Pakoda",
            "DINNER": "Jeera Rice, Paneer Butter Masala (Veg) / Egg Curry, Chapati, Salad"
        }
        for d in days:
            for m_type, items in menu_items.items():
                fm = FoodMenu(
                    property_id=prop1.id,
                    day_of_week=d,
                    meal_type=m_type,
                    items_menu=items,
                    is_veg=(m_type != "DINNER" or d in ["TUESDAY", "THURSDAY"]),
                    special_dietary_notes="Freshly prepared homestyle food"
                )
                db.session.add(fm)

        print("Seeding Complaints...")
        comp1 = Complaint(
            ticket_number="TKT-202602-00412",
            property_id=prop1.id,
            tenant_id=t2.id,
            room_id=r101.id,
            category="WIFI_NETWORK",
            title="Slow Wi-Fi connection in Room 101",
            description="The 5GHz Wi-Fi band signal is weak near the study table. Facing disconnects during office calls.",
            priority="HIGH",
            status="RESOLVED",
            assigned_staff_id=s2.id,
            resolved_at=datetime.now(timezone.utc)
        )
        db.session.add(comp1)
        db.session.flush()

        cu1 = ComplaintUpdate(
            complaint_id=comp1.id,
            updated_by_user_id=manager_user.id,
            status="IN_PROGRESS",
            note="Inspected router signal. Additional repeater installed on 1st floor corridor."
        )
        cu2 = ComplaintUpdate(
            complaint_id=comp1.id,
            updated_by_user_id=manager_user.id,
            status="RESOLVED",
            note="Signal tested at 85 Mbps. Tenant verified connectivity."
        )
        db.session.add_all([cu1, cu2])

        print("Seeding Verified Reviews...")
        rev1 = Review(
            property_id=prop1.id,
            user_id=tenant_user2.id,
            allocation_id=alloc1.id,
            rating=5,
            cleanliness_rating=5,
            food_rating=4,
            comment="Excellent stay so far. Housekeeping is very regular, Wi-Fi problem was fixed quickly by manager Suresh, and food quality is consistent.",
            is_approved=True
        )
        db.session.add(rev1)

        print("Seeding Wishlists and Notifications...")
        w1 = Wishlist(user_id=tenant_user1.id, property_id=prop1.id)
        n1 = Notification(
            user_id=tenant_user2.id,
            title="Rent Invoice Generated",
            message="Your rent invoice for March 2026 is ready for review.",
            notification_type="RENT",
            related_entity_type="rent_invoices",
            related_entity_id=inv2.id
        )
        db.session.add_all([w1, n1])

        # Commit everything
        db.session.commit()
        print("Database seeded successfully with realistic production-ready data!")

if __name__ == "__main__":
    seed_database()
