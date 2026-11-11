from datetime import datetime, timezone
from app.extensions import db

class FoodMenu(db.Model):
    __tablename__ = "food_menus"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey("pg_properties.id", ondelete="CASCADE"), nullable=False)
    day_of_week = db.Column(
        db.Enum("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY", name="day_of_week_type"),
        nullable=False
    )
    meal_type = db.Column(
        db.Enum("BREAKFAST", "LUNCH", "DINNER", "EVENING_SNACKS", name="meal_type_enum"),
        nullable=False
    )
    items_menu = db.Column(db.Text, nullable=False)
    is_veg = db.Column(db.Boolean, default=True, nullable=False)
    special_dietary_notes = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("property_id", "day_of_week", "meal_type", name="uq_property_day_meal"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "day_of_week": self.day_of_week,
            "meal_type": self.meal_type,
            "items_menu": self.items_menu,
            "is_veg": self.is_veg,
            "special_dietary_notes": self.special_dietary_notes,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
