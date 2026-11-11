import os
from flask import Flask, send_from_directory, jsonify
from app.config import config_by_name
from app.extensions import db, migrate, jwt, cors
from app.middleware.error_handlers import register_error_handlers
from app.routes import register_blueprints

def create_app(config_name="development"):
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
        static_url_path="/static"
    )
    
    # Load configuration
    cfg = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "properties"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "complaints"), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ALLOWED_ORIGINS", "*")}},
        supports_credentials=True
    )

    # Register error handlers & routes
    register_error_handlers(app)
    register_blueprints(app)

    # Health check route
    @app.route("/api/health", methods=["GET"])
    def health_check():
        db_status = "connected"
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception as e:
            db_status = f"unreachable: {str(e)}"

        return jsonify({
            "status": "healthy",
            "database": db_status,
            "version": "1.0.0"
        }), 200

    # Serve uploaded media files
    @app.route("/static/uploads/<path:filename>")
    def serve_uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # JWT Error custom callbacks for clear JSON responses
    @jwt.unauthorized_loader
    def custom_unauthorized_response(callback):
        return jsonify({
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Authorization token is missing or invalid.",
                "details": {}
            }
        }), 401

    @jwt.expired_token_loader
    def custom_expired_token_response(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "error": {
                "code": "TOKEN_EXPIRED",
                "message": "The access token has expired. Please refresh your session.",
                "details": {}
            }
        }), 401

    return app
