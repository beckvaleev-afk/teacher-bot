import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./teacher_bot.db")

# AWS
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET: str = os.getenv("S3_BUCKET", "teacher-bot-files")

# GEMINI
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Google Sheets
GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_CREDS_JSON: str = os.getenv("GOOGLE_CREDS_JSON", "google_credentials.json")

# Face WebApp
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://yourdomain.com/face_capture.html")
