import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, OwnerProfile
from app.models.tenant import Tenant
from app.models.property import PGProperty, PropertyFacility
from app.models.room_bed import Room, Bed

@pytest.fixture
def app():
    test_app = create_app("testing")
    with test_app.app_context():
        # Safeguard: ensure test database is isolated and not development or production
        uri = str(test_app.config.get("SQLALCHEMY_DATABASE_URI", ""))
        if not (":memory:" in uri or "test" in uri.lower()):
            raise RuntimeError(
                f"SAFETY GUARD: Refusing to run tests against non-test database: {uri}. "
                "Tests must use an isolated in-memory or designated test database."
            )
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def seeded_users(app):
    with app.app_context():
        # Super Admin
        admin = User(email="admin@test.com", full_name="Test Admin", phone="9876543210", role="SUPER_ADMIN", is_active=True, is_verified=True)
        admin.set_password("Admin@123")
        db.session.add(admin)

        # Owner
        owner = User(email="owner@test.com", full_name="Test Owner", phone="9876543211", role="OWNER", is_active=True, is_verified=True)
        owner.set_password("Owner@123")
        db.session.add(owner)
        db.session.flush()

        profile = OwnerProfile(user_id=owner.id, business_name="Test Stays", is_approved=True)
        db.session.add(profile)
        db.session.flush()

        # Property
        prop = PGProperty(
            owner_id=profile.id,
            name="Alpha PG",
            slug="alpha-pg-test",
            property_type="BOYS",
            address_line1="123 Test St",
            locality="Test Area",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            latitude=12.9716,
            longitude=77.5946,
            contact_phone="9876543211",
            contact_email="owner@test.com",
            description="Test property description",
            is_verified=True,
            is_active=True
        )
        db.session.add(prop)
        db.session.flush()

        fac = PropertyFacility(property_id=prop.id, has_wifi=True, has_ac=True)
        db.session.add(fac)

        # Room and Beds
        room = Room(
            property_id=prop.id,
            room_number="101",
            floor_number=1,
            sharing_type="DOUBLE",
            monthly_rent_per_bed=10000.00,
            security_deposit_per_bed=15000.00,
            is_active=True
        )
        db.session.add(room)
        db.session.flush()

        bed1 = Bed(room_id=room.id, bed_label="Bed A", status="AVAILABLE")
        bed2 = Bed(room_id=room.id, bed_label="Bed B", status="AVAILABLE")
        db.session.add_all([bed1, bed2])

        # Tenant
        tenant_user = User(email="tenant@test.com", full_name="Test Tenant", phone="9876543212", role="TENANT", is_active=True, is_verified=True)
        tenant_user.set_password("Tenant@123")
        db.session.add(tenant_user)
        db.session.flush()

        tenant = Tenant(
            user_id=tenant_user.id,
            emergency_contact_name="Family Contact",
            emergency_contact_phone="9876543299",
            emergency_contact_relation="Parent",
            id_proof_type="Aadhaar",
            id_proof_number_masked="XXXX-1234"
        )
        db.session.add(tenant)

        db.session.commit()

        return {
            "admin_id": admin.id,
            "owner_id": owner.id,
            "tenant_id": tenant_user.id,
            "property_id": prop.id,
            "room_id": room.id,
            "bed1_id": bed1.id,
            "bed2_id": bed2.id
        }

def get_auth_token(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]
