import os
from datetime import timedelta
from dotenv import load_dotenv

# Search for .env in current directory, backend dir, and project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(root_dir, ".env"))
load_dotenv(os.path.join(root_dir, "backend", ".env"))
load_dotenv()

BASE_DIR = root_dir

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "pg-connect-production-secret-key-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "pg-connect-jwt-key-2026")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30")))
    
    # Database URL configuration
    # Can be MySQL (e.g. mysql+pymysql://root:password@localhost:3306/pg_connect_db)
    # or SQLite fallback (sqlite:///pg_connect.db)
    sqlite_path = os.path.join(BASE_DIR, "pg_connect.db")
    default_db_url = f"sqlite:///{sqlite_path}"
    
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", default_db_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine options suitable for both SQLite and MySQL
    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_recycle": 280,
            "pool_pre_ping": True,
        }
    
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024 * 1024)))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "backend", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf"}
    
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5000,http://127.0.0.1:5000,http://localhost:5500,http://127.0.0.1:5500"
        ).split(",") if origin.strip()
    ]

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
