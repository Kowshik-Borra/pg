from app.routes.auth_routes import auth_bp
from app.routes.user_routes import user_bp
from app.routes.property_routes import property_bp
from app.routes.room_bed_routes import room_bed_bp
from app.routes.booking_routes import booking_bp
from app.routes.tenant_routes import tenant_bp
from app.routes.finance_routes import finance_bp
from app.routes.food_routes import food_bp
from app.routes.complaint_routes import complaint_bp
from app.routes.review_routes import review_bp
from app.routes.notification_routes import notification_bp
from app.routes.admin_routes import admin_bp
from app.routes.report_routes import report_bp
from app.routes.map_routes import map_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(property_bp)
    app.register_blueprint(room_bed_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(tenant_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(food_bp)
    app.register_blueprint(complaint_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(map_bp)

