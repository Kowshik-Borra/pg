from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from app.models.user import User

def role_required(*allowed_roles):
    """
    Decorator to enforce Role-Based Access Control on Flask routes.
    Example: @role_required('SUPER_ADMIN', 'OWNER')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role")
            
            if not user_role or user_role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Access denied. Requires one of the following roles: {', '.join(allowed_roles)}.",
                        "details": {}
                    }
                }), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user():
    """
    Helper to fetch the current User instance based on JWT identity (user_id).
    """
    user_id = get_jwt_identity()
    if not user_id:
        return None
    return User.query.get(user_id)
