import re
from app.middleware.error_handlers import APIException

def validate_email(email: str) -> str:
    if not email or not isinstance(email, str):
        raise APIException("Email address is required.", status_code=400, code="VALIDATION_ERROR")
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        raise APIException("Invalid email format.", status_code=400, code="VALIDATION_ERROR")
    return email

def validate_phone(phone: str) -> str:
    if not phone or not isinstance(phone, str):
        raise APIException("Phone number is required.", status_code=400, code="VALIDATION_ERROR")
    clean_phone = re.sub(r"[^\d+]", "", phone.strip())
    # Minimum 10 digits
    digits_only = re.sub(r"\D", "", clean_phone)
    if len(digits_only) < 10 or len(digits_only) > 13:
        raise APIException("Phone number must contain between 10 and 13 digits.", status_code=400, code="VALIDATION_ERROR")
    return clean_phone

def validate_password(password: str) -> str:
    if not password or not isinstance(password, str):
        raise APIException("Password is required.", status_code=400, code="VALIDATION_ERROR")
    if len(password) < 8:
        raise APIException("Password must be at least 8 characters long.", status_code=400, code="VALIDATION_ERROR")
    return password

def validate_coordinates(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        raise APIException("Latitude and Longitude must be valid decimal numbers.", status_code=400, code="VALIDATION_ERROR")
    if not (-90.0 <= lat <= 90.0):
        raise APIException("Latitude must be between -90 and 90.", status_code=400, code="VALIDATION_ERROR")
    if not (-180.0 <= lng <= 180.0):
        raise APIException("Longitude must be between -180 and 180.", status_code=400, code="VALIDATION_ERROR")
    return lat, lng

def validate_positive_amount(amount, field_name="Amount"):
    try:
        val = float(amount)
    except (TypeError, ValueError):
        raise APIException(f"{field_name} must be a valid number.", status_code=400, code="VALIDATION_ERROR")
    if val < 0:
        raise APIException(f"{field_name} cannot be negative.", status_code=400, code="VALIDATION_ERROR")
    return val
