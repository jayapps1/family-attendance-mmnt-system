import os
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------
# PROJECT ROOT
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv(BASE_DIR / ".env", override=True)


# ---------------------------------------------------------
# APPLICATION SETTINGS
# ---------------------------------------------------------

APP_NAME = os.getenv(
    "APP_NAME",
    "Family Attendance Management System"
)


# ---------------------------------------------------------
# DATABASE SETTINGS
# ---------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "family_management_db")
DB_USER = os.getenv("DB_USER", "skilite")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# ---------------------------------------------------------
# STORAGE SETTINGS
# ---------------------------------------------------------

MEDIA_ROOT = BASE_DIR / os.getenv("MEDIA_ROOT", "media")
BACKUP_ROOT = BASE_DIR / os.getenv("BACKUP_ROOT", "backups")


# ---------------------------------------------------------
# SECURITY SETTINGS
# ---------------------------------------------------------

SESSION_TIMEOUT_MINUTES = int(
    os.getenv("SESSION_TIMEOUT_MINUTES", "30")
)


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is missing from the .env file."
    )
# Google Drive for desktop sync destination (configured on this computer).
GOOGLE_DRIVE_BACKUP_DIR = os.getenv("GOOGLE_DRIVE_BACKUP_DIR", "")
