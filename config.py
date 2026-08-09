import os

from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")

API_ID = int(os.getenv("API_ID"))

API_HASH = os.getenv("API_HASH")

# =========================
# RAILWAY PERSISTENT STORAGE
# =========================

RAILWAY_DATA_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")

SESSION_FOLDER = os.path.join(RAILWAY_DATA_PATH, "sessions")

DATABASE_PATH = os.path.join(RAILWAY_DATA_PATH, "database.db")

SUPPORT = "support"

ADMIN_ID = int(os.getenv("ADMIN_ID"))
