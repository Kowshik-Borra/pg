from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from app.models.user import User
from app.extensions import db

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
    return db.session.get(User, user_id)

def verify_property_access(property_id: int, user: User, required_manager_perm: str = None):
    """
    Validates that the authenticated user has legitimate access to the given property_id.
    - SUPER_ADMIN: has access to all properties.
    - OWNER: must own the property through OwnerProfile.
    - MANAGER: must have an active ManagerAssignment for this property.
    Raises APIException(403) if access is denied, or 404 if property doesn't exist.
    """
    from app.models.property import PGProperty
    from app.models.user import OwnerProfile, ManagerAssignment
    from app.middleware.error_handlers import APIException

    if not user:
        raise APIException("Authentication required.", status_code=401, code="UNAUTHORIZED")

    if user.role == "SUPER_ADMIN":
        return True

    prop = db.session.get(PGProperty, property_id)
    if not prop:
        raise APIException("Property not found.", status_code=404, code="NOT_FOUND")

    if user.role == "OWNER":
        profile = OwnerProfile.query.filter_by(user_id=user.id).first()
        if not profile or prop.owner_id != profile.id:
            raise APIException("You do not have permission to manage this property.", status_code=403, code="FORBIDDEN")
        return True

    if user.role == "MANAGER":
        assignment = ManagerAssignment.query.filter_by(
            manager_user_id=user.id,
            property_id=property_id,
            is_active=True
        ).first()
        if not assignment:
            raise APIException("You are not assigned to manage this property.", status_code=403, code="FORBIDDEN")
        if required_manager_perm:
            perm_val = getattr(assignment, required_manager_perm, False)
            if not perm_val:
                raise APIException(f"Permission denied: Missing required permission '{required_manager_perm}'.", status_code=403, code="FORBIDDEN")
        return True

    raise APIException("Access denied.", status_code=403, code="FORBIDDEN")

