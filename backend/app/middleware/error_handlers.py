import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

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
        logger.exception("Unhandled server exception: %s", str(err))
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "details": str(err) if app.config.get("DEBUG") else {}
            }
        }), 500
