import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root and load environment variables from .env
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://campuseats:devpassword@localhost:5432/campuseats",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = bool(os.environ.get("DEBUG", False))


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
