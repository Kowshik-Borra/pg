import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from app.extensions import db

logger = logging.getLogger(__name__)

class APIException(Exception):
    def __init__(self, message, status_code=400, code="BAD_REQUEST", details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}

def register_error_handlers(app):
    @app.errorhandler(APIException)
    def handle_api_exception(err):
        return jsonify({
            "success": False,
            "error": {
                "code": err.code,
                "message": err.message,
                "details": err.details
            }
        }), err.status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(err):
        db.session.rollback()
        logger.warning("Database integrity error: %s", str(err))
        return jsonify({
            "success": False,
            "error": {
                "code": "DATABASE_INTEGRITY_ERROR",
                "message": "A database constraint or duplicate record conflict occurred.",
                "details": str(err.orig) if app.config.get("DEBUG") and hasattr(err, "orig") else {}
            }
        }), 409

    @app.errorhandler(OperationalError)
    def handle_operational_error(err):
        db.session.rollback()
        logger.error("MySQL operational error: %s", str(err))
        return jsonify({
            "success": False,
            "error": {
                "code": "DATABASE_CONNECTION_ERROR",
                "message": "Database service is unavailable or connection failed. Please ensure MySQL Server 8.0 is running and credentials in .env are correct.",
                "details": str(err.orig) if app.config.get("DEBUG") and hasattr(err, "orig") else {}
            }
        }), 503

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(err):
        db.session.rollback()
        logger.error("SQLAlchemy database error: %s", str(err))
        return jsonify({
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": "A database operation error occurred.",
                "details": str(err) if app.config.get("DEBUG") else {}
            }
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        return jsonify({
            "success": False,
            "error": {
                "code": err.name.upper().replace(" ", "_"),
                "message": err.description,
                "details": {}
            }
        }), err.code

    @app.errorhandler(Exception)
    def handle_generic_exception(err):
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.exception("Unhandled server exception: %s", str(err))
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "details": str(err) if app.config.get("DEBUG") else {}
            }
        }), 500

