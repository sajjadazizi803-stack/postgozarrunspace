import os

from dotenv import load_dotenv

load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"❌ متغیر محیطی {name} در Railway تنظیم نشده است.")

    return value


BOT_TOKEN = get_required_env("BOT_TOKEN")

API_ID = int(get_required_env("API_ID"))

API_HASH = get_required_env("API_HASH")

ADMIN_ID = int(get_required_env("ADMIN_ID"))


# =========================
# RAILWAY PERSISTENT STORAGE
# =========================

RAILWAY_DATA_PATH = os.getenv(
    "RAILWAY_VOLUME_MOUNT_PATH",
    "/data",
)

SESSION_FOLDER = os.path.join(
    RAILWAY_DATA_PATH,
    "sessions",
)

DATABASE_PATH = os.path.join(
    RAILWAY_DATA_PATH,
    "database.db",
)


SUPPORT = "support"
