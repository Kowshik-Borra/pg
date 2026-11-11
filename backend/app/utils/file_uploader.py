import os
import uuid
from werkzeug.utils import secure_filename
from app.middleware.error_handlers import APIException

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file_obj, upload_folder: str, subfolder: str = "properties") -> str:
    """
    Saves an uploaded file with a randomized safe filename and returns the relative path.
    """
    if not file_obj or not file_obj.filename:
        raise APIException("No file provided for upload.", status_code=400, code="VALIDATION_ERROR")
    
    if not allowed_file(file_obj.filename):
        raise APIException("File type not allowed. Allowed types: PNG, JPG, JPEG, WEBP, PDF.", status_code=400, code="VALIDATION_ERROR")
    
    ext = file_obj.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    target_dir = os.path.join(upload_folder, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, unique_name)
    file_obj.save(file_path)
    
    # Return relative URL path
    return f"/static/uploads/{subfolder}/{unique_name}"
