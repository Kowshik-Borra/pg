import os
import urllib.parse
from datetime import timedelta
from dotenv import load_dotenv

# Search for .env in current directory, backend dir, and project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(root_dir, ".env"))
load_dotenv(os.path.join(root_dir, "backend", ".env"))
load_dotenv()

BASE_DIR = root_dir

def build_mysql_uri():
    """
    Constructs a safe MySQL database connection URL with PyMySQL.
    Encodes special characters in username and password.
    Fails fast if MySQL configuration is missing.
    """
    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        # Prevent silent SQLite fallback during application runtime
        if env_db_url.startswith("sqlite"):
            raise ValueError(
                "SQLite is disabled for application runtime. PG Connect requires MySQL 8.0. "
                "Please configure a valid MySQL DATABASE_URL in .env (e.g. mysql+pymysql://user:password@localhost:3306/pg_connect_db)."
            )
        if env_db_url.startswith("mysql://"):
            env_db_url = env_db_url.replace("mysql://", "mysql+pymysql://", 1)
        return env_db_url

    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db_name = os.getenv("MYSQL_DB", "pg_connect_db")

    encoded_user = urllib.parse.quote_plus(user)
    encoded_password = urllib.parse.quote_plus(password)

    return f"mysql+pymysql://{encoded_user}:{encoded_password}@{host}:{port}/{db_name}?charset=utf8mb4"

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "pg-connect-production-secret-key-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "pg-connect-jwt-key-2026")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30")))

    # Enforce MySQL 8.0
    SQLALCHEMY_DATABASE_URI = build_mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
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
            "http://localhost:5000,http://127.0.0.1:5000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://127.0.0.1:3000"
        ).split(",") if origin.strip()
    ]

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    # Test environment uses designated test database or isolated in-memory engine
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {}

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
